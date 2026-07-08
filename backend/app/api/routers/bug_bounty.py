"""Standalone autonomous bug bounty hunt API."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.agents.bug_bounty_agent import BugBountyAgent
from app.core.config import get_settings
from app.db.base import AsyncSessionLocal
from app.models.engagement import AgentRun, Engagement, EngagementStatus, Finding, Target
from app.services.methodology_runner import get_pipeline_options
from app.services.report_writer import save_agent_reports
from app.tools.wordlists import wordlist_status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bug-bounty", tags=["bug-bounty"])
settings = get_settings()


class HuntRequest(BaseModel):
    target_url: str
    scope_domains: list[str] = Field(default_factory=list)
    max_iterations: int = Field(15, ge=1, le=30)
    notes: str = ""
    run_methodology: bool = True
    pipeline_mode: Literal["default", "full", "custom"] = "default"
    methodology_phases: list[str] = Field(default_factory=list)


_jobs: dict[str, dict] = {}


@router.get("/methodology")
async def methodology_info():
    return get_pipeline_options()


@router.get("/wordlists")
async def hunt_wordlist_status():
    return wordlist_status()


async def _persist_hunt_result(
    job_id: str,
    body: HuntRequest,
    scope: list[str],
    result,
) -> dict:
    """Save hunt to DB and auto-generate reports."""
    from urllib.parse import urlparse

    host = urlparse(body.target_url).hostname or body.target_url
    async with AsyncSessionLocal() as db:
        eng = Engagement(
            name=f"Bug Bounty Hunt — {host}",
            description=f"{body.target_url}\n{body.notes}".strip(),
            status=EngagementStatus.COMPLETED.value,
            owner_id=1,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.add(eng)
        await db.flush()

        target_obj = Target(
            engagement_id=eng.id,
            name=host,
            target_type="web",
            url=body.target_url,
            notes=body.notes or None,
        )
        db.add(target_obj)
        await db.flush()

        run = AgentRun(
            engagement_id=eng.id,
            agent_name="BugBountyAgent",
            status=result.status,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=result.duration_seconds,
            findings_count=len(result.findings),
            tool_outputs=result.tool_outputs,
            error_message=result.error,
        )
        db.add(run)
        await db.flush()

        target_dict = {
            "id": target_obj.id,
            "name": target_obj.name,
            "url": target_obj.url,
            "target_type": target_obj.target_type,
        }

        for f in result.findings:
            finding_kwargs = {k: v for k, v in f.items() if k in Finding.__table__.columns}
            db.add(Finding(agent_run_id=run.id, target_id=target_obj.id, **finding_kwargs))

        reports = await save_agent_reports(
            db,
            engagement_id=eng.id,
            engagement_name=eng.name,
            agent_run_id=run.id,
            agent_name="BugBountyAgent",
            target=target_dict,
            result=result,
        )
        await db.commit()

        return {
            "engagement_id": eng.id,
            "agent_run_id": run.id,
            "reports": reports,
        }


@router.post("/hunt")
async def start_hunt(body: HuntRequest, background_tasks: BackgroundTasks):
    import uuid
    from urllib.parse import urlparse

    job_id = str(uuid.uuid4())[:8]
    scope = body.scope_domains or []
    if not scope:
        host = urlparse(body.target_url).hostname
        if host:
            scope = [host]

    _jobs[job_id] = {"status": "running", "target": body.target_url}

    async def run():
        agent = BugBountyAgent()
        target = {
            "url": body.target_url,
            "target_type": "web",
            "notes": body.notes,
        }
        ctx = {
            "scope_domains": scope,
            "target_url": body.target_url,
            "job_id": job_id,
            "max_iterations": body.max_iterations,
            "run_methodology": body.run_methodology,
            "pipeline_mode": body.pipeline_mode,
            "methodology_phases": body.methodology_phases or None,
        }
        try:
            result = await agent.run(target, ctx)
            persist = await _persist_hunt_result(job_id, body, scope, result)
            _jobs[job_id] = {
                "status": "completed" if result.status == "success" else "failed",
                "target": body.target_url,
                "findings": result.findings,
                "tool_calls": result.tool_outputs.get("tool_calls", []),
                "tool_events": result.tool_outputs.get("tool_events", []),
                "summary": result.tool_outputs.get("final_answer", ""),
                "iterations": result.tool_outputs.get("iterations"),
                "recon_summary": result.tool_outputs.get("recon_summary"),
                "methodology_pipeline": result.tool_outputs.get("methodology_pipeline"),
                "error": result.error,
                "engagement_id": persist["engagement_id"],
                "reports": persist["reports"],
            }
        except Exception as exc:
            logger.exception("Hunt job %s failed", job_id)
            _jobs[job_id] = {"status": "failed", "error": str(exc)}

    background_tasks.add_task(run)
    return {
        "job_id": job_id,
        "status": "running",
        "target": body.target_url,
        "methodology_enabled": body.run_methodology,
        "pipeline_mode": body.pipeline_mode,
    }


@router.get("/hunt/{job_id}")
async def hunt_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Hunt job not found")
    return {"job_id": job_id, **job}
