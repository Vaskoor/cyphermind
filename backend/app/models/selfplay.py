"""Self-play Red vs Blue match models."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class SelfPlayGame(Base):
    __tablename__ = "selfplay_games"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_code: Mapped[str] = mapped_column(Text)
    target_language: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    winner: Mapped[Optional[str]] = mapped_column(String(8))   # "red" or "blue"
    total_rounds: Mapped[int] = mapped_column(Integer, default=0)
    novel_patterns_found: Mapped[int] = mapped_column(Integer, default=0)
    ingested_to_kb: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    moves: Mapped[list["SelfPlayMove"]] = relationship("SelfPlayMove", back_populates="game")

class SelfPlayMove(Base):
    __tablename__ = "selfplay_moves"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("selfplay_games.id"))
    round_number: Mapped[int] = mapped_column(Integer)
    team: Mapped[str] = mapped_column(String(8))     # "red" or "blue"
    move_type: Mapped[str] = mapped_column(String(64))  # attack or defense
    content: Mapped[str] = mapped_column(Text)
    succeeded: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_novel: Mapped[bool] = mapped_column(Boolean, default=False)
    novelty_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game: Mapped["SelfPlayGame"] = relationship("SelfPlayGame", back_populates="moves")
