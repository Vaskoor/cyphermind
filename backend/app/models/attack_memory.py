"""Persistent attack memory — findings, payloads, self-play patterns."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AttackMemory(Base):
    """Stores proven attack patterns for retrieval into future hunts."""

    __tablename__ = "attack_memories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(32), index=True)  # finding, payload, attack_pattern, tool_hint
    source: Mapped[str] = mapped_column(String(32), default="engagement")  # engagement, bug_bounty, selfplay
    target_type: Mapped[str] = mapped_column(String(64), default="web", index=True)
    tech_stack: Mapped[Optional[str]] = mapped_column(String(256))  # comma-separated
    vuln_type: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    title: Mapped[str] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)
    payload: Mapped[Optional[str]] = mapped_column(Text)
    url_pattern: Mapped[Optional[str]] = mapped_column(String(1024))
    success_score: Mapped[float] = mapped_column(Float, default=1.0)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    rag_chunk_id: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
