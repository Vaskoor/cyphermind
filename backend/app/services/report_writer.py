"""Persist auto-generated reports after agent runs."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engagement import Report
from app.services.report_service import generate_agent_html_report, generate_recon_html_report

if TYPE_CHECKING:
    from app.agents.base import AgentResult

logger = logging.getLogger(__name__)


def _has_recon_data(agent_name: str, tool_outputs: dict | None) -> bool:
    if not tool_outputs:
        return False
    if agent_name == "ReconAgent":
        return bool(tool_outputs.get("nmap") or tool_outputs.get("subfinder"))
    if agent_name == "BugBountyAgent":
        return bool(
            tool_outputs.get("methodology_pipeline")
            or tool_outputs.get("recon_summary")
            or tool_outputs.get("recon_briefing")
        )
    return bool(tool_outputs)


async def save_agent_reports(
    db: AsyncSession,
    *,
    engagement_id: int,
    engagement_name: str,
    agent_run_id: int,
    agent_name: str,
    target: dict,
    result: "AgentResult",
) -> list[dict]:
    """
    Auto-generate and persist reports after an agent completes.
    Returns list of {id, title, report_type, findings_count}.
    """
    created: list[dict] = []
    tool_outputs = result.tool_outputs or {}
    findings = result.findings or []

    # 1. Recon report (when recon data exists)
    if _has_recon_data(agent_name, tool_outputs):
        recon_html = generate_recon_html_report(
            engagement_name, agent_name, target, tool_outputs
        )
        recon_report = Report(
            engagement_id=engagement_id,
            agent_run_id=agent_run_id,
            title=f"{agent_name} — Recon Report",
            format="html",
            report_type="recon",
            agent_name=agent_name,
            findings_count=0,
            content=recon_html,
        )
        db.add(recon_report)
        await db.flush()
        created.append({
            "id": recon_report.id,
            "title": recon_report.title,
            "report_type": "recon",
            "findings_count": 0,
        })
        logger.info("Created recon report id=%s for %s", recon_report.id, agent_name)

    # 2. Combined agent report (findings + summary + any remaining recon)
    combined_html = generate_agent_html_report(
        engagement_name,
        agent_name,
        target,
        findings,
        tool_outputs,
        report_type="combined",
    )
    combined_report = Report(
        engagement_id=engagement_id,
        agent_run_id=agent_run_id,
        title=f"{agent_name} — Assessment Report",
        format="html",
        report_type="combined",
        agent_name=agent_name,
        findings_count=len(findings),
        content=combined_html,
    )
    db.add(combined_report)
    await db.flush()
    created.append({
        "id": combined_report.id,
        "title": combined_report.title,
        "report_type": "combined",
        "findings_count": len(findings),
    })
    logger.info("Created combined report id=%s for %s", combined_report.id, agent_name)

    # 3. Executive summary-only report for BugBountyAgent when LLM wrote a summary
    final_answer = tool_outputs.get("final_answer")
    if agent_name == "BugBountyAgent" and final_answer:
        exec_html = generate_agent_html_report(
            engagement_name,
            agent_name,
            target,
            findings,
            {**tool_outputs, "methodology_pipeline": None},  # summary focus
            report_type="combined",
        )
        exec_report = Report(
            engagement_id=engagement_id,
            agent_run_id=agent_run_id,
            title=f"{agent_name} — Executive Summary",
            format="html",
            report_type="executive",
            agent_name=agent_name,
            findings_count=len(findings),
            content=exec_html,
        )
        db.add(exec_report)
        await db.flush()
        created.append({
            "id": exec_report.id,
            "title": exec_report.title,
            "report_type": "executive",
            "findings_count": len(findings),
        })

    return created
