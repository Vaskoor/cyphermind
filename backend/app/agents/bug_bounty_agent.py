"""Autonomous LLM-driven bug bounty hunter with tool calling."""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from app.agents.base import AgentResult, BaseAgent
from app.core.config import get_settings
from app.learning.phase_q_learning import phase_q_learner
from app.services.agent_loop import run_agent_loop
from app.services.attack_memory_service import retrieve_attack_context
from app.services.learning_hooks import after_bug_bounty_hunt
from app.services.methodology_runner import run_pre_hunt_pipeline
from app.tools.methodology import FULL_PIPELINE

logger = logging.getLogger(__name__)
settings = get_settings()


class BugBountyAgent(BaseAgent):
    name = "BugBountyAgent"
    description = (
        "Autonomous bug bounty copilot: 13-phase methodology, attack memory, "
        "phase Q-learning, RAG enrichment, scope-aware reporting"
    )

    async def run(self, target: dict, context: dict) -> AgentResult:
        url = target.get("url") or target.get("ip_address") or ""
        scope_domains = context.get("scope_domains") or []
        if not scope_domains and url:
            host = urlparse(url if "://" in url else f"https://{url}").hostname
            if host:
                scope_domains = [host]

        max_iterations = context.get("max_iterations", settings.bug_bounty_max_iterations)
        on_event = context.get("on_event")
        findings: list[dict] = []
        tool_log: list[dict] = []
        pipeline_result: dict | None = None

        domain = scope_domains[0] if scope_domains else urlparse(url).hostname or url
        run_pipeline = context.get("run_methodology", settings.run_methodology_on_hunt)
        target_type = target.get("target_type", "web")
        tech_stack = target.get("tech_stack") or []
        if isinstance(tech_stack, str):
            tech_stack = [tech_stack]

        loop_ctx = {
            "scope_domains": scope_domains,
            "target_url": url,
            "target_domain": domain,
            "job_id": context.get("job_id") or url or domain,
            "findings_collector": findings,
        }

        async def event_bridge(event_type: str, data: dict):
            tool_log.append({"event": event_type, **data})
            if on_event:
                await on_event(event_type, data)

        # Load learned attack intelligence from past hunts + self-play
        try:
            attack_ctx = await retrieve_attack_context(
                target_type=target_type,
                tech_stack=tech_stack,
                domain=domain,
            )
            if attack_ctx.get("prompt_block"):
                loop_ctx["attack_intelligence"] = attack_ctx["prompt_block"]
                await event_bridge("attack_memory_loaded", {
                    "memories": len(attack_ctx.get("db_memories") or []),
                    "rag_chunks": len(attack_ctx.get("rag_chunks") or []),
                })
        except Exception as exc:
            logger.warning("Attack memory retrieval failed: %s", exc)

        # Phase 0: Q-learned methodology pipeline
        if run_pipeline and domain:
            pipeline_mode = context.get("pipeline_mode", settings.methodology_pipeline_mode)
            if pipeline_mode == "full":
                phases = FULL_PIPELINE
            elif context.get("methodology_phases"):
                phases = context.get("methodology_phases")
            else:
                phases = phase_q_learner.select_phases(
                    target_type=target_type,
                    tech_stack=tech_stack,
                    mode="default",
                )
                await event_bridge("phases_selected", {
                    "phases": phases,
                    "source": "phase_q_learning",
                })

            try:
                pipeline_result = await run_pre_hunt_pipeline(
                    domain,
                    phases=phases,
                    context=loop_ctx,
                    on_event=event_bridge,
                )
                loop_ctx.update({
                    "recon_briefing": pipeline_result.get("briefing", ""),
                    "recon_summary": pipeline_result.get("summary", {}),
                })
            except Exception as exc:
                logger.warning("Methodology pipeline failed (continuing with LLM): %s", exc)
                tool_log.append({"event": "methodology_error", "error": str(exc)})

        goal = self._build_goal(target, scope_domains, pipeline_result)

        try:
            result = await run_agent_loop(
                goal,
                context=loop_ctx,
                max_iterations=max_iterations,
                on_event=event_bridge,
                temperature=0.35,
            )
            findings = result.findings or findings

            agent_result = AgentResult(
                agent_name=self.name,
                status="success",
                findings=findings,
                tool_outputs={
                    "final_answer": result.final_answer,
                    "iterations": result.iterations,
                    "tool_calls": result.tool_calls_made,
                    "tool_events": tool_log,
                    "status": result.status,
                    "methodology_pipeline": pipeline_result,
                    "recon_summary": loop_ctx.get("recon_summary"),
                },
            )

            # Learn from this hunt for next time
            try:
                await after_bug_bounty_hunt(
                    agent_result,
                    target,
                    pipeline_result=pipeline_result,
                )
            except Exception as exc:
                logger.warning("Post-hunt learning failed: %s", exc)

            return agent_result
        except Exception as exc:
            logger.exception("BugBountyAgent failed")
            return AgentResult(
                agent_name=self.name,
                status="failed",
                findings=findings,
                tool_outputs={
                    "tool_events": tool_log,
                    "methodology_pipeline": pipeline_result,
                },
                error=str(exc),
            )

    def _build_goal(
        self,
        target: dict,
        scope_domains: list[str],
        pipeline_result: dict | None = None,
    ) -> str:
        parts = [
            "Conduct a thorough bug bounty security assessment using the Cybernote 2026 methodology.",
            f"Target type: {target.get('target_type', 'web')}",
        ]
        if target.get("url"):
            parts.append(f"URL: {target['url']}")
        if target.get("ip_address"):
            parts.append(f"IP: {target['ip_address']}")
        if scope_domains:
            parts.append(f"In-scope domains: {', '.join(scope_domains)}")
        if target.get("tech_stack"):
            parts.append(f"Tech stack hints: {target['tech_stack']}")

        if pipeline_result:
            summary = pipeline_result.get("summary", {})
            parts.append(
                f"\nAutomated recon completed: {summary.get('subdomains', 0)} subdomains, "
                f"{summary.get('alive_hosts', 0)} alive hosts, {summary.get('urls', 0)} URLs."
            )
            parts.append(
                "Use LEARNED ATTACK INTELLIGENCE in system context — reuse proven payloads and techniques."
            )
        else:
            parts.append("\nRun methodology pipeline phases, prioritizing learned patterns from memory.")

        parts.append(
            "\nFor each vulnerability: enrich_finding_with_rag → report_finding → final summary."
        )
        return "\n".join(parts)
