"""Findings list router with pagination."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.engagement import AgentRun, Finding
from app.schemas.engagement import FindingOut

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("")
async def list_findings(
    engagement_id: int | None = Query(None),
    severity: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(Finding)
    count_q = select(func.count()).select_from(Finding)

    if engagement_id is not None:
        run_ids_q = select(AgentRun.id).where(AgentRun.engagement_id == engagement_id)
        run_result = await db.execute(run_ids_q)
        run_ids = list(run_result.scalars().all())
        filter_clause = Finding.agent_run_id.in_(run_ids) if run_ids else Finding.id == -1
        q = q.where(filter_clause)
        count_q = count_q.where(filter_clause)

    if severity:
        q = q.where(Finding.severity == severity.lower())
        count_q = count_q.where(Finding.severity == severity.lower())

    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    q = q.order_by(Finding.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(q)
    items = [FindingOut.model_validate(f) for f in result.scalars().all()]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
    }
