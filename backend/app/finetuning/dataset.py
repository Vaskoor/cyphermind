"""Build fine-tuning datasets from hunts, findings, and self-play."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.finetuning.state import DATASET_DIR
from app.models.attack_memory import AttackMemory
from app.models.engagement import Finding
from app.models.selfplay import SelfPlayMove

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are CypherMind, an elite bug bounty hunter and penetration testing copilot. "
    "Find real vulnerabilities, explain exploitation, and provide PoC payloads."
)


async def _load_findings(limit: int = 500) -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Finding).order_by(Finding.created_at.desc()).limit(limit)
        )
        rows = result.scalars().all()
    return [
        {
            "title": f.title,
            "description": f.description or "",
            "severity": f.severity,
            "payload": f.payload,
            "cwe_id": f.cwe_id,
            "cve_id": f.cve_id,
        }
        for f in rows
    ]


async def _load_attack_memories(limit: int = 500) -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AttackMemory).order_by(AttackMemory.success_score.desc()).limit(limit)
        )
        rows = result.scalars().all()
    return [
        {
            "title": m.title,
            "content": m.content,
            "payload": m.payload,
            "vuln_type": m.vuln_type,
            "severity": m.severity,
            "source": m.source,
        }
        for m in rows
    ]


async def _load_selfplay_attacks(limit: int = 200) -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SelfPlayMove)
            .where(SelfPlayMove.team == "red", SelfPlayMove.is_novel == True)  # noqa: E712
            .order_by(SelfPlayMove.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
    return [{"content": m.content, "round": m.round_number} for m in rows]


def _finding_to_messages(finding: dict) -> dict[str, Any]:
    user = (
        f"Analyze and report this security finding for a bug bounty program.\n"
        f"Title: {finding['title']}\n"
        f"Severity hint: {finding['severity']}"
    )
    parts = [finding.get("description") or ""]
    if finding.get("payload"):
        parts.append(f"PoC payload: {finding['payload']}")
    if finding.get("cwe_id"):
        parts.append(f"CWE: {finding['cwe_id']}")
    assistant = "\n".join(parts).strip()
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }


def _memory_to_messages(mem: dict) -> dict[str, Any]:
    user = f"How would you exploit or test for {mem.get('vuln_type', 'this vulnerability')}?"
    assistant = mem.get("content", "")
    if mem.get("payload"):
        assistant += f"\n\nPayload: {mem['payload']}"
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant.strip()},
        ]
    }


def _selfplay_to_messages(attack: dict) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": "You are a red-team penetration tester."},
            {"role": "user", "content": "Generate a realistic attack technique for the given code context."},
            {"role": "assistant", "content": attack.get("content", "")},
        ]
    }


async def build_dataset(
    *,
    include_findings: bool = True,
    include_memories: bool = True,
    include_selfplay: bool = True,
    max_samples: int = 2000,
) -> dict:
    """
    Export JSONL dataset for OpenAI/NVIDIA-compatible fine-tuning.
    Returns metadata with path and sample counts.
    """
    examples: list[dict] = []

    if include_findings:
        for f in await _load_findings():
            if f.get("description") or f.get("payload"):
                examples.append(_finding_to_messages(f))

    if include_memories:
        for m in await _load_attack_memories():
            if m.get("content"):
                examples.append(_memory_to_messages(m))

    if include_selfplay:
        for a in await _load_selfplay_attacks():
            if a.get("content"):
                examples.append(_selfplay_to_messages(a))

    examples = examples[:max_samples]

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = DATASET_DIR / f"cyphermind_train_{ts}.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    meta = {
        "path": str(out_path),
        "filename": out_path.name,
        "total_samples": len(examples),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "format": "openai_chat_jsonl",
    }
    logger.info("Fine-tuning dataset built: %s (%d samples)", out_path, len(examples))
    return meta


def list_datasets() -> list[dict]:
    files = sorted(DATASET_DIR.glob("cyphermind_train_*.jsonl"), reverse=True)
    out = []
    for p in files[:20]:
        lines = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
        out.append({
            "filename": p.name,
            "path": str(p),
            "samples": lines,
            "size_bytes": p.stat().st_size,
        })
    return out
