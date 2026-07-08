"""Self-play arena router."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from app.db.base import AsyncSessionLocal, get_db
from app.models.selfplay import SelfPlayGame, SelfPlayMove
from app.services.selfplay_service import run_selfplay_game

router = APIRouter(prefix="/selfplay", tags=["selfplay"])


class SelfPlayRequest(BaseModel):
    target_code: str
    language: str = "python"
    max_rounds: int = 5


@router.post("/start")
async def start_selfplay(body: SelfPlayRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    game = SelfPlayGame(
        target_code=body.target_code[:10000],
        target_language=body.language,
        status="running",
    )
    db.add(game)
    await db.commit()
    await db.refresh(game)
    game_id = game.id

    async def run_and_save():
        async with AsyncSessionLocal() as session:
            result = await run_selfplay_game(body.target_code, body.language, body.max_rounds)
            g = await session.get(SelfPlayGame, game_id)
            if not g:
                return
            g.status = "completed"
            g.winner = result["winner"]
            g.total_rounds = result["total_rounds"]
            g.novel_patterns_found = result["novel_patterns_found"]
            g.ingested_to_kb = result.get("ingested_to_kb", 0) > 0
            g.completed_at = datetime.utcnow()
            for r in result["rounds"]:
                session.add(SelfPlayMove(
                    game_id=game_id,
                    round_number=r["round"],
                    team="red",
                    move_type="attack",
                    content=r["red_move"],
                    is_novel=r["is_novel"],
                ))
                session.add(SelfPlayMove(
                    game_id=game_id,
                    round_number=r["round"],
                    team="blue",
                    move_type="defense",
                    content=r["blue_move"],
                ))
            await session.commit()

    background_tasks.add_task(run_and_save)
    return {"game_id": game.id, "status": "started"}


@router.get("/status/{game_id}")
async def game_status(game_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SelfPlayGame).where(SelfPlayGame.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(404, "Game not found")
    return {
        "id": game.id,
        "status": game.status,
        "winner": game.winner,
        "total_rounds": game.total_rounds,
        "novel_patterns_found": game.novel_patterns_found,
        "ingested_to_kb": game.ingested_to_kb,
    }
