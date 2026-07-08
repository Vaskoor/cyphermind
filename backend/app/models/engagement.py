"""Engagement, Target, AgentRun, Finding, Evidence, Report models."""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum

class EngagementStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class SeverityLevel(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class Engagement(Base):
    __tablename__ = "engagements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=EngagementStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    owner: Mapped["User"] = relationship("User", back_populates="engagements")
    targets: Mapped[list["Target"]] = relationship("Target", back_populates="engagement")
    agent_runs: Mapped[list["AgentRun"]] = relationship("AgentRun", back_populates="engagement")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="engagement")

class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.id"))
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64))  # web, network, code, binary
    url: Mapped[Optional[str]] = mapped_column(String(1024))
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    code_path: Mapped[Optional[str]] = mapped_column(String(1024))
    tech_stack: Mapped[Optional[str]] = mapped_column(JSON)   # list of technologies
    open_ports: Mapped[Optional[str]] = mapped_column(JSON)   # list of ports
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    engagement: Mapped["Engagement"] = relationship("Engagement", back_populates="targets")
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="target")

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.id"))
    agent_name: Mapped[str] = mapped_column(String(64))  # ReconAgent, SASTAgent, etc.
    status: Mapped[str] = mapped_column(String(32), default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_outputs: Mapped[Optional[str]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    rl_state: Mapped[Optional[str]] = mapped_column(String(256))
    rl_action: Mapped[Optional[int]] = mapped_column(Integer)
    rl_reward: Mapped[Optional[float]] = mapped_column(Float)

    engagement: Mapped["Engagement"] = relationship("Engagement", back_populates="agent_runs")
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="agent_run")

class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    agent_run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id"))
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id"))
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[Optional[str]] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16), default=SeverityLevel.MEDIUM)
    cve_id: Mapped[Optional[str]] = mapped_column(String(64))
    cwe_id: Mapped[Optional[str]] = mapped_column(String(64))
    cvss_score: Mapped[Optional[float]] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_novel: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[Optional[str]] = mapped_column(Text)
    attack_chain: Mapped[Optional[str]] = mapped_column(JSON)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024))
    line_number: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent_run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="findings")
    target: Mapped["Target"] = relationship("Target", back_populates="findings")
    evidence: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="finding")

class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"))
    evidence_type: Mapped[str] = mapped_column(String(64))  # screenshot, log, request, response
    content: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    finding: Mapped["Finding"] = relationship("Finding", back_populates="evidence")

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    engagement_id: Mapped[int] = mapped_column(ForeignKey("engagements.id"))
    agent_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_runs.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    format: Mapped[str] = mapped_column(String(16), default="html")  # html, pdf, json, sarif
    report_type: Mapped[str] = mapped_column(String(32), default="combined")  # recon, findings, combined, executive
    agent_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024))
    agent_combo: Mapped[Optional[str]] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    engagement: Mapped["Engagement"] = relationship("Engagement", back_populates="reports")
