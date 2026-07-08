"""Engagement orchestrator — runs agents sequentially with event broadcasting."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.models.engagement import (
    AgentRun,
    Engagement,
    EngagementStatus,
    Finding,
    Target,
)
from app.services.report_writer import save_agent_reports
from app.services.learning_hooks import after_agent_run
from app.learning.policy_selector import load_bt_scores, record_engagement_outcome, select_agents
from app.learning.q_learning import compute_reward
from app.agents.recon_agent import ReconAgent
from app.agents.sast_agent import SASTAgent
from app.agents.exploit_agent import ExploitAgent
from app.agents.postexploit_agent import PostExploitAgent
from app.agents.bug_bounty_agent import BugBountyAgent
from app.core import events

logger = logging.getLogger(__name__)

AGENT_MAP = {
    "ReconAgent": ReconAgent,
    "SASTAgent": SASTAgent,
    "ExploitAgent": ExploitAgent,
    "PostExploitAgent": PostExploitAgent,
    "BugBountyAgent": BugBountyAgent,
}


def _target_to_dict(target: Target) -> dict:
    return {
        "id": target.id,
        "name": target.name,
        "target_type": target.target_type,
        "url": target.url,
        "ip_address": target.ip_address,
        "code_path": target.code_path,
        "tech_stack": target.tech_stack or [],
        "open_ports": target.open_ports or [],
        "notes": target.notes,
    }


class EngagementOrchestrator:
    async def _publish(self, engagement_id: int, event_type: str, data: dict | None = None):
        await events.publish(
            f"engagement:{engagement_id}",
            {"type": event_type, "engagement_id": engagement_id, **(data or {})},
        )

    async def run_engagement(
        self,
        engagement_id: int,
        agent_names: Optional[list[str]] = None,
        target_id: Optional[int] = None,
        mode: str = "standard",
        scope_domains: Optional[list[str]] = None,
        max_iterations: int = 15,
    ) -> dict:
        all_findings: list[dict] = []
        start = datetime.utcnow()
        used_agents: list[str] = []

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Engagement).where(Engagement.id == engagement_id)
            )
            eng = result.scalar_one_or_none()
            if not eng:
                raise ValueError(f"Engagement {engagement_id} not found")

            eng.status = EngagementStatus.RUNNING.value
            eng.started_at = datetime.utcnow()
            await db.commit()
            await self._publish(engagement_id, "engagement_started", {"status": "running"})

            tgt_q = select(Target).where(Target.engagement_id == engagement_id)
            if target_id:
                tgt_q = tgt_q.where(Target.id == target_id)
            tgt_result = await db.execute(tgt_q)
            target_obj = tgt_result.scalars().first()
            if not target_obj:
                eng.status = EngagementStatus.FAILED.value
                await db.commit()
                await self._publish(
                    engagement_id, "engagement_failed", {"error": "No target found"}
                )
                raise ValueError("No target found for engagement")

            target = _target_to_dict(target_obj)

            bt_scores = await load_bt_scores(db)

            if mode in ("bug_bounty", "autonomous"):
                agent_names = agent_names or ["BugBountyAgent"]
                selection_reason = "bug_bounty_mode"
            elif agent_names:
                selection_reason = "manual"
            else:
                agent_names, _, selection_reason = select_agents(
                    target.get("target_type", "web"),
                    target.get("tech_stack") or [],
                    len(target.get("open_ports") or []),
                    bt_scores=bt_scores,
                    mode=mode,
                )

            used_agents = list(agent_names)
            await self._publish(
                engagement_id,
                "agents_selected",
                {"agents": used_agents, "reason": selection_reason},
            )

            async def on_event(event_type: str, data: dict):
                await self._publish(engagement_id, event_type, data)

            agent_context = {
                "scope_domains": scope_domains or [],
                "max_iterations": max_iterations,
                "mode": mode,
                "on_event": on_event,
            }

            for name in agent_names:
                cls = AGENT_MAP.get(name)
                if not cls:
                    continue

                await self._publish(engagement_id, "agent_started", {"agent": name})
                agent = cls()
                run = AgentRun(
                    engagement_id=engagement_id,
                    agent_name=name,
                    status="running",
                    started_at=datetime.utcnow(),
                )
                db.add(run)
                await db.flush()

                result_run = await agent.safe_run(target, agent_context)
                run.status = result_run.status
                run.completed_at = datetime.utcnow()
                run.duration_seconds = result_run.duration_seconds
                run.findings_count = len(result_run.findings)
                run.tool_outputs = result_run.tool_outputs
                if result_run.error:
                    run.error_message = result_run.error

                for f in result_run.findings:
                    finding_kwargs = {
                        k: v for k, v in f.items() if k in Finding.__table__.columns
                    }
                    finding = Finding(
                        agent_run_id=run.id,
                        target_id=target["id"],
                        **finding_kwargs,
                    )
                    db.add(finding)
                    await db.flush()
                    await self._publish(
                        engagement_id,
                        "finding_discovered",
                        {
                            "id": finding.id,
                            "title": finding.title,
                            "severity": finding.severity,
                            "agent": name,
                        },
                    )
                all_findings.extend(result_run.findings)

                # Auto-generate recon + assessment reports after each agent
                try:
                    report_records = await save_agent_reports(
                        db,
                        engagement_id=engagement_id,
                        engagement_name=eng.name,
                        agent_run_id=run.id,
                        agent_name=name,
                        target=target,
                        result=result_run,
                    )
                    await self._publish(
                        engagement_id,
                        "report_generated",
                        {
                            "agent": name,
                            "agent_run_id": run.id,
                            "reports": report_records,
                        },
                    )
                except Exception as exc:
                    logger.exception("Failed to generate report for %s: %s", name, exc)

                # Learn from this agent run (memory + phase Q for BugBountyAgent)
                try:
                    await after_agent_run(name, result_run, target, source="engagement")
                    await self._publish(
                        engagement_id,
                        "learning_updated",
                        {"agent": name, "findings": len(result_run.findings)},
                    )
                except Exception as exc:
                    logger.warning("Learning hooks failed for %s: %s", name, exc)

                await db.commit()

                await self._publish(
                    engagement_id,
                    "agent_completed",
                    {
                        "id": run.id,
                        "agent_name": name,
                        "agent": name,
                        "status": result_run.status,
                        "findings_count": len(result_run.findings),
                        "duration_seconds": result_run.duration_seconds,
                        "started_at": run.started_at.isoformat() if run.started_at else None,
                        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    },
                )

            eng.status = EngagementStatus.COMPLETED.value
            eng.completed_at = datetime.utcnow()
            await db.commit()
            await self._publish(engagement_id, "status_update", {"status": "completed"})

            tech_stack = target.get("tech_stack") or []
            novel_count = sum(1 for f in all_findings if f.get("is_novel"))
            elapsed = (datetime.utcnow() - start).total_seconds()
            record_engagement_outcome(
                target.get("target_type", "web"),
                tech_stack,
                len(target.get("open_ports") or []),
                used_agents,
                all_findings,
                novel_count,
                elapsed,
            )
            severity_scores = [
                {"critical": 10, "high": 7, "medium": 4, "low": 1}.get(
                    f.get("severity", "low"), 1
                )
                for f in all_findings
            ]
            reward = compute_reward(len(all_findings), severity_scores, novel_count, elapsed)

            await self._publish(
                engagement_id,
                "engagement_completed",
                {
                    "status": "completed",
                    "findings_count": len(all_findings),
                    "agents": used_agents,
                    "rl_reward": reward,
                },
            )

            return {
                "status": "completed",
                "agents": used_agents,
                "findings_count": len(all_findings),
                "rl_reward": reward,
            }


orchestrator = EngagementOrchestrator()
