"""Learning and feedback router."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.db.base import get_db
from app.models.learning import PreferencePair
from app.learning.q_learning import q_orchestrator
from app.learning.phase_q_learning import phase_q_learner
from app.learning.bradley_terry import fit_bradley_terry
from app.services.attack_memory_service import get_memory_stats

router = APIRouter(prefix="/learning", tags=["learning"])


class FeedbackRequest(BaseModel):
    query: str
    report_a: str
    report_b: str
    winner: str   # "a" or "b"
    agent_combo_a: Optional[str] = None
    agent_combo_b: Optional[str] = None
    analyst_notes: Optional[str] = None


@router.get("/q-table")
async def get_q_table():
    return q_orchestrator.get_policy_summary()


@router.get("/phase-policy")
async def get_phase_policy():
    """Q-learned methodology phase rankings per target profile."""
    return phase_q_learner.get_policy_summary()


@router.get("/attack-memory")
async def get_attack_memory_stats():
    """Stats on stored attack patterns from hunts + self-play."""
    return await get_memory_stats()


@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    pair = PreferencePair(
        analyst_id=1,
        **body.model_dump()
    )
    db.add(pair)
    await db.commit()
    await db.refresh(pair)
    return {"id": pair.id, "status": "recorded", "message": "Preference saved — will influence future agent selection via Bradley-Terry"}


@router.get("/bradley-terry")
async def get_bt_scores(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PreferencePair))
    pairs = result.scalars().all()
    bt_pairs = [
        (p.agent_combo_a or "unknown_a", p.agent_combo_b or "unknown_b", p.winner)
        for p in pairs
        if p.agent_combo_a and p.agent_combo_b
    ]
    scores = fit_bradley_terry(bt_pairs) if bt_pairs else {}
    return {"scores": scores, "pair_count": len(bt_pairs)}


@router.get("/summary")
async def learning_summary(db: AsyncSession = Depends(get_db)):
    """Unified view of all learning systems."""
    memory = await get_memory_stats()
    q_policy = q_orchestrator.get_policy_summary()
    phase_policy = phase_q_learner.get_policy_summary()

    result = await db.execute(select(PreferencePair))
    pairs = result.scalars().all()
    bt_pairs = [
        (p.agent_combo_a, p.agent_combo_b, p.winner)
        for p in pairs
        if p.agent_combo_a and p.agent_combo_b
    ]
    bt = fit_bradley_terry(bt_pairs) if bt_pairs else {}

    return {
        "attack_memory": memory,
        "agent_q_learning": {
            "states_learned": len(q_policy.get("states", {})),
            "engagements": q_policy.get("engagement_count", 0),
            "epsilon": q_policy.get("epsilon"),
        },
        "phase_q_learning": {
            "states_learned": len(phase_policy.get("states", {})),
            "hunts": phase_policy.get("hunt_count", 0),
            "epsilon": phase_policy.get("epsilon"),
        },
        "bradley_terry": {"scores": bt, "pairs": len(bt_pairs)},
        "llm_fine_tuning": False,
        "learning_mode": "memory + Q-tables + RAG ingestion (no model weight updates)",
    }
