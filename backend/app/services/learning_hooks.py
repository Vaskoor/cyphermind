"""Post-hunt learning hooks — wire memory, phase Q, without LLM fine-tuning."""
from __future__ import annotations

import logging
from typing import Optional

from app.agents.base import AgentResult
from app.learning.phase_q_learning import phase_q_learner
from app.services.attack_memory_service import (
    store_finding_memories,
    store_tool_sequence_hint,
)

logger = logging.getLogger(__name__)


async def after_bug_bounty_hunt(
    result: AgentResult,
    target: dict,
    *,
    source: str = "bug_bounty",
    pipeline_result: dict | None = None,
):
    """Run all learning updates after a bug bounty hunt completes."""
    target_type = target.get("target_type", "web")
    tech_stack = target.get("tech_stack") or []
    if isinstance(tech_stack, str):
        tech_stack = [tech_stack]
    findings = result.findings or []
    tool_outputs = result.tool_outputs or {}

    # 1. Store findings in attack memory + RAG
    if findings:
        await store_finding_memories(
            findings,
            target_type=target_type,
            tech_stack=tech_stack,
            source=source,
            target_url=target.get("url") or "",
        )

    # 2. Learn successful tool sequences
    tool_calls = tool_outputs.get("tool_calls") or []
    if tool_calls and findings:
        await store_tool_sequence_hint(tool_calls, findings, target_type, source)

    # 3. Update phase Q-learning from pipeline results
    pipeline = pipeline_result or tool_outputs.get("methodology_pipeline")
    if isinstance(pipeline, dict):
        inner = pipeline.get("pipeline") if "pipeline" in pipeline else pipeline
        if isinstance(inner, dict):
            phase_q_learner.update_from_pipeline(target_type, tech_stack, inner, findings)
        else:
            phase_q_learner.update_from_pipeline(target_type, tech_stack, pipeline, findings)

    logger.info(
        "Learning hooks complete: %d findings stored, phase Q updated",
        len(findings),
    )

    # Optional: export fine-tuning dataset after successful hunts
    try:
        from app.finetuning.pipeline import maybe_auto_export
        await maybe_auto_export()
    except Exception as exc:
        logger.debug("Fine-tuning auto-export skipped: %s", exc)


async def after_agent_run(
    agent_name: str,
    result: AgentResult,
    target: dict,
    *,
    source: str = "engagement",
):
    """Learning updates after any agent completes in an engagement."""
    # BugBountyAgent runs full learning hooks internally after its loop
    if agent_name == "BugBountyAgent":
        return

    if result.findings:
        await store_finding_memories(
            result.findings,
            target_type=target.get("target_type", "web"),
            tech_stack=target.get("tech_stack") or [],
            source=source,
            target_url=target.get("url") or "",
        )
