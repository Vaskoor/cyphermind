"""Agent execution router."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.engagement import Engagement
from app.services.orchestrator import orchestrator
from app.learning.q_learning import q_orchestrator

router = APIRouter(prefix="/agents", tags=["agents"])


class ExecuteRequest(BaseModel):
    engagement_id: int
    target_id: Optional[int] = None
    agent_name: Optional[str] = None
    mode: Literal["standard", "bug_bounty", "autonomous"] = "standard"
    scope_domains: list[str] = Field(default_factory=list)
    max_iterations: int = Field(15, ge=1, le=30)


@router.post("/execute")
async def execute_agents(
    body: ExecuteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Engagement).where(Engagement.id == body.engagement_id))
    eng = result.scalar_one_or_none()
    if not eng:
        raise HTTPException(404, "Engagement not found")

    if body.agent_name:
        agent_names = [body.agent_name]
    elif body.mode in ("bug_bounty", "autonomous"):
        agent_names = ["BugBountyAgent"]
    else:
        agent_names = None

    background_tasks.add_task(
        orchestrator.run_engagement,
        body.engagement_id,
        agent_names,
        body.target_id,
        body.mode,
        body.scope_domains,
        body.max_iterations,
    )
    return {
        "status": "started",
        "engagement_id": body.engagement_id,
        "mode": body.mode,
        "agents": agent_names or ["RL selection"],
    }


@router.get("/q-policy")
async def get_q_policy():
    return q_orchestrator.get_policy_summary()
