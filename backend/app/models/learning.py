"""RL Q-Table, ExperienceReplay, PreferencePair models."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class QTable(Base):
    """Stores Q-values for (state, action) pairs."""
    __tablename__ = "q_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    state_key: Mapped[str] = mapped_column(String(256), index=True)
    action: Mapped[int] = mapped_column(Integer)          # bitmask 0-15 of 4 agents
    q_value: Mapped[float] = mapped_column(Float, default=0.0)
    visit_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ExperienceReplay(Base):
    """Experience replay buffer for Q-learning updates."""
    __tablename__ = "experience_replay"

    id: Mapped[int] = mapped_column(primary_key=True)
    state: Mapped[str] = mapped_column(String(256))
    action: Mapped[int] = mapped_column(Integer)
    reward: Mapped[float] = mapped_column(Float)
    next_state: Mapped[str] = mapped_column(String(256))
    done: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PreferencePair(Base):
    """Human feedback — pairwise preference for Bradley-Terry model."""
    __tablename__ = "preference_pairs"

    id: Mapped[int] = mapped_column(primary_key=True)
    analyst_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    query: Mapped[str] = mapped_column(Text)
    report_a: Mapped[str] = mapped_column(Text)
    report_b: Mapped[str] = mapped_column(Text)
    winner: Mapped[str] = mapped_column(String(8))          # "a" or "b"
    agent_combo_a: Mapped[Optional[str]] = mapped_column(String(256))
    agent_combo_b: Mapped[Optional[str]] = mapped_column(String(256))
    analyst_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    analyst: Mapped["User"] = relationship("User", back_populates="preferences")
