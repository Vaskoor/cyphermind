"""Dashboard statistics router."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.engagement import AgentRun, Engagement, EngagementStatus, Finding

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    eng_counts = {}
    for status in EngagementStatus:
        r = await db.execute(
            select(func.count()).select_from(Engagement).where(Engagement.status == status.value)
        )
        eng_counts[status.value] = r.scalar() or 0

    severity_counts = {}
    for sev in ("critical", "high", "medium", "low", "info"):
        r = await db.execute(
            select(func.count()).select_from(Finding).where(Finding.severity == sev)
        )
        severity_counts[sev] = r.scalar() or 0

    runs_result = await db.execute(
        select(AgentRun).order_by(AgentRun.started_at.desc()).limit(10)
    )
    recent_activity = [
        {
            "id": run.id,
            "engagement_id": run.engagement_id,
            "agent_name": run.agent_name,
            "status": run.status,
            "findings_count": run.findings_count,
            "started_at": run.started_at.isoformat() if run.started_at else None,
        }
        for run in runs_result.scalars().all()
    ]

    return {
        "engagements": eng_counts,
        "findings_by_severity": severity_counts,
        "recent_activity": recent_activity,
    }
