"""Automated bug bounty methodology pipeline — runs phases before LLM analysis."""
from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from app.tools.methodology import DEFAULT_PIPELINE, FULL_PIPELINE, METHODOLOGY_PHASES
from app.tools.recon_tools import RECON_STATE, _get_state, run_methodology_pipeline

EventCallback = Callable[[str, dict], Awaitable[None]]


def format_pipeline_for_llm(pipeline_result: dict, max_chars: int = 14000) -> str:
    """Compress pipeline output into LLM-readable recon briefing."""
    lines = [
        "# Recon Intelligence Briefing (Methodology Pipeline)",
        f"Domain: {pipeline_result.get('domain', 'unknown')}",
    ]
    summary = pipeline_result.get("summary", {})
    lines.append(
        f"Subdomains: {summary.get('subdomains', 0)} | "
        f"Alive: {summary.get('alive_hosts', 0)} | "
        f"URLs: {summary.get('urls', 0)} | "
        f"JS files: {summary.get('js_urls', 0)}"
    )
    lines.append("")

    for phase_name, phase_data in pipeline_result.get("phases", {}).items():
        lines.append(f"## Phase: {phase_name}")
        if isinstance(phase_data, dict):
            if phase_data.get("error"):
                lines.append(f"  Error: {phase_data['error']}")
            elif phase_data.get("skipped"):
                lines.append(f"  Skipped: {phase_data.get('reason', '')}")
            else:
                # Include key fields only
                for key in ("count", "subdomains", "alive", "urls", "secrets", "candidates", "vulnerable", "categories", "found", "files", "results", "open_ports"):
                    if key in phase_data and phase_data[key]:
                        val = phase_data[key]
                        if isinstance(val, list):
                            preview = val[:15]
                            lines.append(f"  {key} ({len(val)}): {json.dumps(preview, default=str)[:800]}")
                        elif isinstance(val, dict):
                            lines.append(f"  {key}: {json.dumps(val, default=str)[:600]}")
                        else:
                            lines.append(f"  {key}: {val}")
        lines.append("")

    text = "\n".join(lines)
    return text[:max_chars]


async def run_pre_hunt_pipeline(
    domain: str,
    *,
    phases: list[str] | None = None,
    context: dict | None = None,
    on_event: EventCallback | None = None,
) -> dict[str, Any]:
    """
    Execute methodology phases sequentially, emit progress events,
    return structured result + LLM briefing text.
    """
    ctx = dict(context or {})
    ctx.setdefault("job_id", ctx.get("target_url") or domain)
    phase_list = phases or ctx.get("methodology_phases") or DEFAULT_PIPELINE

    if on_event:
        await on_event("methodology_started", {"domain": domain, "phases": phase_list})

    pipeline_result = await run_methodology_pipeline(domain, phase_list, ctx)
    briefing = format_pipeline_for_llm(pipeline_result)

    state = _get_state(ctx)
    ctx["recon_briefing"] = briefing
    ctx["recon_summary"] = pipeline_result.get("summary", {})
    ctx["recon_subdomains"] = sorted(state["subdomains"])[:200]
    ctx["recon_alive_hosts"] = sorted(state["alive_hosts"])[:100]
    ctx["recon_urls"] = sorted(state["urls"])[:300]

    if on_event:
        await on_event("methodology_completed", {
            "domain": domain,
            "summary": pipeline_result.get("summary"),
            "phases_run": list(pipeline_result.get("phases", {}).keys()),
        })

    return {
        "pipeline": pipeline_result,
        "briefing": briefing,
        "summary": pipeline_result.get("summary"),
    }


def list_methodology_phases() -> list[dict]:
    return METHODOLOGY_PHASES


def get_pipeline_options() -> dict:
    return {
        "default": DEFAULT_PIPELINE,
        "full": FULL_PIPELINE,
        "phases": METHODOLOGY_PHASES,
    }


def clear_recon_state(job_id: str | None = None):
    if job_id and job_id in RECON_STATE:
        del RECON_STATE[job_id]
    elif not job_id:
        RECON_STATE.clear()
