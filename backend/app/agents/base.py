"""Base agent class all specialized agents inherit from."""
from __future__ import annotations
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class AgentResult:
    agent_name: str
    status: str             # success | failed | partial
    findings: list[dict] = field(default_factory=list)
    tool_outputs: dict = field(default_factory=dict)
    duration_seconds: float = 0.0
    error: Optional[str] = None

class BaseAgent(ABC):
    """Abstract base for all CypherMind agents."""

    name: str = "BaseAgent"
    description: str = ""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def run(self, target: dict, context: dict) -> AgentResult:
        """Execute agent on target. Override in subclass."""
        ...

    async def safe_run(self, target: dict, context: dict) -> AgentResult:
        """Wrapper with timing and error handling."""
        start = time.time()
        try:
            result = await self.run(target, context)
        except Exception as exc:
            self.logger.error(f"{self.name} failed: {exc}", exc_info=True)
            result = AgentResult(
                agent_name=self.name,
                status="failed",
                error=str(exc),
            )
        result.duration_seconds = time.time() - start
        return result

    def _make_finding(
        self,
        title: str,
        severity: str,
        description: str = "",
        cwe_id: Optional[str] = None,
        cve_id: Optional[str] = None,
        payload: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        confidence: float = 0.7,
    ) -> dict:
        return {
            "title": title,
            "severity": severity,
            "description": description,
            "cwe_id": cwe_id,
            "cve_id": cve_id,
            "payload": payload,
            "file_path": file_path,
            "line_number": line_number,
            "confidence": confidence,
            "is_novel": False,
        }
