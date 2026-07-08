"""Autonomous LLM agent loop with tool calling (ReAct pattern)."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from app.services.llm_service import chat_completion_raw, parse_react_tool_calls
from app.tools.registry import tool_registry

# Ensure tools are registered
import app.tools.bootstrap  # noqa: F401

logger = logging.getLogger(__name__)

EventCallback = Callable[[str, dict], Awaitable[None]]


@dataclass
class AgentLoopResult:
    final_answer: str
    messages: list[dict]
    tool_calls_made: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    iterations: int = 0
    status: str = "completed"


BUG_BOUNTY_SYSTEM = """You are CypherMind — an elite autonomous bug bounty hunter implementing the Cybernote 2026 methodology.

MISSION: Find real, reportable security vulnerabilities in the authorized target scope.

METHODOLOGY (13 phases — use tools in this order when recon data is insufficient):
1. Passive Subdomain Enum — passive_subdomain_enum, certificate_transparency
2. Active Subdomain Bruteforce — subdomain_bruteforce, subdomain_fuzz
3. Infrastructure Mapping — asn_lookup, reverse_dns
4. WAF/Origin Discovery — web_search (historical DNS, favicon hash), http_probe
5. Alive Host Detection — merge_subdomains, httpx_alive_check
6. VHOST Enumeration — vhost_fuzz on discovered IPs
7. URL/Endpoint Discovery — wayback_urls, crawl_urls, categorize_urls
8. JS Analysis — extract_js_urls, js_secret_scan
9. Directory Discovery — directory_fuzz, sensitive_file_scan
10. GitHub Intel — github_recon
11. Port Scanning — port_scan, run_nmap
12. Vuln Scanning — run_nuclei, run_nuclei_exposures
13. Subdomain Takeover — subdomain_takeover_check

Or run the full automated pipeline: run_methodology_pipeline(domain, pipeline_mode="default"|"full")

RULES:
1. ONLY test targets within scope_domains. Use check_scope before active probing.
2. A recon briefing may be pre-loaded — prioritize high-signal URLs (auth, admin, API, IDOR candidates).
3. **LEARNED ATTACK INTELLIGENCE** may be pre-loaded from past hunts and self-play — REUSE proven payloads and techniques first before inventing new ones.
4. Use enrich_finding_with_rag, search_knowledge_base, and search_attack_memory when analyzing vulns.
5. Use web_search for recent CVEs, exploit writeups, and technology-specific tips.
6. When you find a vulnerability, call report_finding with title, severity, description, CWE, PoC.
7. Methodology phases were Q-learned from past hunts — trust high-signal recon data already collected.
8. Final answer: executive summary of findings with severity breakdown.

Available tool categories: recon, scan, exploit, intel, scope, reporting.
"""


async def run_agent_loop(
    user_goal: str,
    *,
    system_prompt: str = BUG_BOUNTY_SYSTEM,
    context: dict | None = None,
    max_iterations: int = 15,
    tool_names: list[str] | None = None,
    on_event: EventCallback | None = None,
    temperature: float = 0.4,
    llm_role: str = "bug_bounty",
) -> AgentLoopResult:
    """
    Run autonomous tool-calling loop until model stops or max_iterations reached.
    """
    ctx = dict(context or {})
    findings_collector: list[dict] = []
    ctx["findings_collector"] = findings_collector

    tools = tool_registry.openai_schemas(tool_names)
    scope_note = ""
    if ctx.get("scope_domains"):
        scope_note = f"\n\nSCOPE (in-scope domains): {', '.join(ctx['scope_domains'])}"
    if ctx.get("target_url"):
        scope_note += f"\nPRIMARY TARGET: {ctx['target_url']}"
    if ctx.get("recon_briefing"):
        scope_note += f"\n\nPRE-COMPUTED RECON BRIEFING:\n{ctx['recon_briefing'][:12000]}"
    if ctx.get("attack_intelligence"):
        scope_note += f"\n\n{ctx['attack_intelligence'][:8000]}"

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt + scope_note},
        {"role": "user", "content": user_goal},
    ]

    tool_calls_made: list[dict] = []

    async def emit(event_type: str, data: dict):
        if on_event:
            await on_event(event_type, data)

    for iteration in range(1, max_iterations + 1):
        await emit("agent_thinking", {"iteration": iteration})

        message = await chat_completion_raw(
            messages,
            tools=tools if tools else None,
            temperature=temperature,
            max_tokens=8192,
            role=ctx.get("llm_role") or llm_role,
        )

        tool_calls = message.get("tool_calls") or []

        # Native OpenAI-style tool calls
        if tool_calls:
            messages.append(message)
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    args = {"raw": raw_args}

                await emit("tool_call_started", {"tool": name, "arguments": args, "iteration": iteration})
                result = await tool_registry.execute(name, args, ctx)
                tool_calls_made.append({"tool": name, "arguments": args, "result": result})
                await emit("tool_call_completed", {"tool": name, "result": result, "iteration": iteration})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{iteration}_{name}"),
                    "name": name,
                    "content": json.dumps(result, default=str)[:12000],
                })
            continue

        content = message.get("content") or ""

        # Fallback: parse text-based tool calls from Kimi
        react_calls = parse_react_tool_calls(content)
        if react_calls:
            messages.append({"role": "assistant", "content": content})
            for call in react_calls:
                name = call["name"]
                args = call.get("arguments", {})
                await emit("tool_call_started", {"tool": name, "arguments": args, "iteration": iteration})
                result = await tool_registry.execute(name, args, ctx)
                tool_calls_made.append({"tool": name, "arguments": args, "result": result})
                await emit("tool_call_completed", {"tool": name, "result": result, "iteration": iteration})
                messages.append({
                    "role": "user",
                    "content": f"Tool `{name}` result:\n{json.dumps(result, default=str)[:12000]}",
                })
            continue

        # No tool calls — final answer
        messages.append({"role": "assistant", "content": content})
        await emit("agent_completed", {"iteration": iteration, "summary": content[:500]})
        return AgentLoopResult(
            final_answer=content,
            messages=messages,
            tool_calls_made=tool_calls_made,
            findings=findings_collector,
            iterations=iteration,
            status="completed",
        )

    # Max iterations
    summary = "Max iterations reached. Partial results collected."
    await emit("agent_completed", {"iteration": max_iterations, "summary": summary, "partial": True})
    return AgentLoopResult(
        final_answer=summary,
        messages=messages,
        tool_calls_made=tool_calls_made,
        findings=findings_collector,
        iterations=max_iterations,
        status="max_iterations",
    )
