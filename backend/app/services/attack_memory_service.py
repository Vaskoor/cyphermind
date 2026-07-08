"""Attack memory — store and retrieve proven patterns for future hunts."""
from __future__ import annotations

import logging
import re
import uuid
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.models.attack_memory import AttackMemory
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

SEVERITY_SCORE = {"critical": 10, "high": 7, "medium": 4, "low": 2, "info": 0.5}


def _infer_vuln_type(title: str, description: str = "") -> str:
    text = f"{title} {description}".lower()
    for vtype, pattern in [
        ("sqli", r"sql.?inject"),
        ("xss", r"xss|cross.?site"),
        ("ssrf", r"ssrf|server.?side.?request"),
        ("idor", r"idor|insecure.?direct"),
        ("auth", r"auth.?bypass|broken.?auth"),
        ("rce", r"rce|remote.?code|command.?inject"),
        ("secrets", r"secret|api.?key|token|credential"),
        ("takeover", r"takeover|subdomain"),
    ]:
        if re.search(pattern, text):
            return vtype
    return "general"


async def _ingest_to_rag(memory: AttackMemory) -> str | None:
    """Dual-write: store in RAG for semantic retrieval."""
    chunk_id = f"attack_mem_{memory.id or uuid.uuid4().hex[:12]}"
    content = (
        f"[{memory.memory_type.upper()}] {memory.title}\n"
        f"Target: {memory.target_type} | Vuln: {memory.vuln_type}\n"
        f"{memory.content}\n"
        f"Payload: {memory.payload or 'N/A'}\n"
        f"URL pattern: {memory.url_pattern or 'N/A'}"
    )
    try:
        rag_service.add_chunk(
            chunk_id=chunk_id,
            content=content,
            metadata={
                "source": f"attack_memory:{memory.source}",
                "type": memory.memory_type,
                "vuln_type": memory.vuln_type or "",
                "severity": memory.severity,
            },
        )
        return chunk_id
    except Exception as exc:
        logger.warning("RAG ingest failed for attack memory: %s", exc)
        return None


async def store_finding_memories(
    findings: list[dict],
    *,
    target_type: str = "web",
    tech_stack: list[str] | None = None,
    source: str = "engagement",
    target_url: str = "",
) -> int:
    """Persist confirmed findings as attack memories."""
    if not findings:
        return 0

    stack_str = ",".join(tech_stack or [])
    stored = 0

    async with AsyncSessionLocal() as db:
        for f in findings:
            severity = (f.get("severity") or "medium").lower()
            score = SEVERITY_SCORE.get(severity, 2.0)
            if f.get("is_verified"):
                score *= 1.5
            if f.get("is_novel"):
                score *= 1.3

            mem = AttackMemory(
                memory_type="finding",
                source=source,
                target_type=target_type,
                tech_stack=stack_str or None,
                vuln_type=_infer_vuln_type(f.get("title", ""), f.get("description", "")),
                severity=severity,
                title=f.get("title", "Untitled finding")[:512],
                content=(f.get("description") or "")[:4000],
                payload=(f.get("payload") or "")[:2000] or None,
                url_pattern=target_url or f.get("url") or None,
                success_score=score,
            )
            db.add(mem)
            await db.flush()
            mem.rag_chunk_id = await _ingest_to_rag(mem)
            stored += 1

        await db.commit()

    logger.info("Stored %d finding memories (source=%s)", stored, source)
    return stored


async def store_selfplay_patterns(
    rounds: list[dict],
    language: str = "python",
) -> int:
    """Ingest novel self-play red team attacks into memory + RAG."""
    stored = 0
    async with AsyncSessionLocal() as db:
        for r in rounds:
            if not r.get("is_novel"):
                continue
            red_move = (r.get("red_move") or "").strip()
            if not red_move or red_move.startswith("[Red team error"):
                continue

            mem = AttackMemory(
                memory_type="attack_pattern",
                source="selfplay",
                target_type="code",
                tech_stack=language,
                vuln_type="general",
                severity="medium",
                title=f"Self-play attack pattern (round {r.get('round', '?')})",
                content=red_move[:4000],
                payload=red_move[:2000],
                success_score=3.0,
            )
            db.add(mem)
            await db.flush()
            mem.rag_chunk_id = await _ingest_to_rag(mem)
            stored += 1

        await db.commit()

    logger.info("Stored %d self-play attack patterns", stored)
    return stored


async def store_tool_sequence_hint(
    tool_calls: list[dict],
    findings: list[dict],
    target_type: str = "web",
    source: str = "bug_bounty",
) -> int:
    """Learn which tool sequences led to findings."""
    if not tool_calls or not findings:
        return 0

    tools_used = []
    for tc in tool_calls:
        name = tc.get("tool") or (tc.get("result") or {}).get("tool")
        if name:
            tools_used.append(name)

    if len(tools_used) < 2:
        return 0

    sequence = " → ".join(tools_used[-12:])
    content = (
        f"Successful tool sequence ({len(findings)} findings):\n{sequence}\n"
        f"Findings: {', '.join(f.get('title', '?')[:40] for f in findings[:5])}"
    )

    async with AsyncSessionLocal() as db:
        mem = AttackMemory(
            memory_type="tool_hint",
            source=source,
            target_type=target_type,
            vuln_type="general",
            severity="info",
            title=f"Tool sequence → {len(findings)} finding(s)",
            content=content,
            success_score=min(len(findings) * 2.0, 10.0),
        )
        db.add(mem)
        await db.flush()
        mem.rag_chunk_id = await _ingest_to_rag(mem)
        await db.commit()

    return 1


async def retrieve_attack_context(
    target_type: str = "web",
    tech_stack: list[str] | None = None,
    domain: str = "",
    top_k: int = 8,
) -> dict:
    """
    Retrieve relevant attack memories from DB + RAG.
    Returns formatted context for agent prompt injection.
    """
    stack_str = ",".join(tech_stack or [])
    query_parts = [target_type, stack_str, domain, "attack payload vulnerability exploit"]
    query = " ".join(p for p in query_parts if p)

    # RAG semantic search
    rag_chunks = []
    try:
        rag_chunks = rag_service.retrieve(query, top_k=top_k)
    except Exception as exc:
        logger.warning("RAG retrieve failed: %s", exc)

    # DB structured memories
    db_memories: list[AttackMemory] = []
    async with AsyncSessionLocal() as db:
        stmt = (
            select(AttackMemory)
            .where(AttackMemory.target_type.in_([target_type, "code", "web"]))
            .order_by(desc(AttackMemory.success_score), desc(AttackMemory.created_at))
            .limit(top_k)
        )
        result = await db.execute(stmt)
        db_memories = list(result.scalars().all())

        # Bump use_count for retrieved memories
        for m in db_memories[:5]:
            m.use_count += 1
        await db.commit()

    return {
        "db_memories": db_memories,
        "rag_chunks": rag_chunks,
        "prompt_block": format_attack_context(db_memories, rag_chunks),
    }


def format_attack_context(
    db_memories: list[AttackMemory],
    rag_chunks: list,
    max_chars: int = 8000,
) -> str:
    """Format memories into LLM-readable learned intelligence block."""
    lines = [
        "## LEARNED ATTACK INTELLIGENCE (from past hunts + self-play — use these patterns)",
        "",
    ]

    if db_memories:
        lines.append("### Proven findings & payloads from memory")
        for i, m in enumerate(db_memories[:6], 1):
            lines.append(f"{i}. [{m.severity.upper()}] {m.title}")
            if m.vuln_type:
                lines.append(f"   Type: {m.vuln_type} | Source: {m.source}")
            if m.content:
                lines.append(f"   {m.content[:400]}")
            if m.payload:
                lines.append(f"   PoC: {m.payload[:200]}")
            lines.append("")

    if rag_chunks:
        lines.append("### Semantically related attack knowledge (RAG)")
        seen = set()
        for c in rag_chunks[:5]:
            snippet = c.content[:350]
            if snippet in seen:
                continue
            seen.add(snippet)
            lines.append(f"- {snippet}")
            lines.append("")

    if len(lines) <= 3:
        return ""

    text = "\n".join(lines)
    return text[:max_chars]


async def get_memory_stats() -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AttackMemory))
        all_mem = list(result.scalars().all())

    by_type: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for m in all_mem:
        by_type[m.memory_type] = by_type.get(m.memory_type, 0) + 1
        by_source[m.source] = by_source.get(m.source, 0) + 1

    return {
        "total": len(all_mem),
        "by_type": by_type,
        "by_source": by_source,
        "top_patterns": [
            {"title": m.title, "score": m.success_score, "uses": m.use_count}
            for m in sorted(all_mem, key=lambda x: x.success_score, reverse=True)[:10]
        ],
    }
