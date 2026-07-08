"""Engagements CRUD router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.base import get_db
from app.models.engagement import Engagement, Target, AgentRun, Finding
from app.schemas.engagement import EngagementCreate, EngagementOut, FindingOut
from app.services.threat_model import generate_threat_model

router = APIRouter(prefix="/engagements", tags=["engagements"])


def _engagement_to_out(eng: Engagement, findings: list | None = None) -> dict:
    out = EngagementOut.model_validate(eng).model_dump()
    if findings is not None:
        out["findings"] = [FindingOut.model_validate(f).model_dump() for f in findings]
    return out

@router.post("", response_model=EngagementOut, status_code=201)
async def create_engagement(body: EngagementCreate, db: AsyncSession = Depends(get_db)):
    scope_note = ""
    if body.scope_domains:
        scope_note = f"\n[scope:{','.join(body.scope_domains)}]"
    eng = Engagement(
        name=body.name,
        description=(body.description or "") + scope_note,
        owner_id=1,
    )
    db.add(eng)
    await db.flush()
    for t in body.targets:
        data = t.model_dump(exclude={"scope_domains"})
        if t.scope_domains:
            data["notes"] = (data.get("notes") or "") + f" scope:{','.join(t.scope_domains)}"
        db.add(Target(engagement_id=eng.id, **data))
    await db.commit()
    await db.refresh(eng)
    return eng

@router.get("", response_model=list[EngagementOut])
async def list_engagements(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.agent_runs), selectinload(Engagement.targets))
    )
    return result.scalars().all()


@router.get("/{engagement_id}", response_model=EngagementOut)
async def get_engagement(engagement_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Engagement)
        .options(
            selectinload(Engagement.agent_runs),
            selectinload(Engagement.targets),
        )
        .where(Engagement.id == engagement_id)
    )
    eng = result.scalar_one_or_none()
    if not eng:
        raise HTTPException(404, "Engagement not found")

    runs_result = await db.execute(
        select(AgentRun.id).where(AgentRun.engagement_id == engagement_id)
    )
    run_ids = list(runs_result.scalars().all())
    findings = []
    if run_ids:
        findings_result = await db.execute(
            select(Finding).where(Finding.agent_run_id.in_(run_ids))
        )
        findings = list(findings_result.scalars().all())

    return _engagement_to_out(eng, findings)


@router.get("/{engagement_id}/threat-model")
async def get_threat_model(engagement_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.targets))
        .where(Engagement.id == engagement_id)
    )
    eng = result.scalar_one_or_none()
    if not eng:
        raise HTTPException(404, "Engagement not found")
    target = eng.targets[0] if eng.targets else {}
    target_dict = {
        "target_type": getattr(target, "target_type", "web"),
        "url": getattr(target, "url", None),
        "code_path": getattr(target, "code_path", None),
        "ip_address": getattr(target, "ip_address", None),
        "tech_stack": getattr(target, "tech_stack", None) or [],
        "open_ports": getattr(target, "open_ports", None) or [],
    }
    return generate_threat_model(target_dict)

@router.delete("/{engagement_id}", status_code=204)
async def delete_engagement(engagement_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    eng = result.scalar_one_or_none()
    if not eng:
        raise HTTPException(404, "Engagement not found")
    await db.delete(eng)
    await db.commit()
