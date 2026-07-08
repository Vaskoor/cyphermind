"""
Phase Q-Learning for Bug Bounty Methodology
============================================
Learns which recon/exploit phases produce the best results per target profile.
Persisted to data/phase_q_table.json — no LLM fine-tuning.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import random
from typing import Optional

from app.core.config import PROJECT_ROOT
from app.tools.methodology import DEFAULT_PIPELINE, FULL_PIPELINE, PHASE_BY_NAME

logger = logging.getLogger(__name__)

PHASE_Q_PATH = PROJECT_ROOT / "data" / "phase_q_table.json"

# Phases eligible for Q-learning selection (high-impact subset)
LEARNABLE_PHASES = list(dict.fromkeys(DEFAULT_PIPELINE + [
    "passive_subdomain_enum",
    "subdomain_bruteforce",
    "infrastructure_mapping",
    "wayback_urls",
    "crawl_urls",
    "js_secret_scan",
    "directory_fuzz",
    "github_recon",
    "port_scan",
    "vuln_scanning",
    "subdomain_takeover_check",
]))


def encode_phase_state(target_type: str, tech_stack: list[str] | None = None) -> str:
    stack = ",".join(sorted((tech_stack or [])[:5]))
    key = f"{target_type}|{stack}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def _phase_reward(phase_name: str, phase_result: dict, hunt_findings: list[dict]) -> float:
    """Estimate per-phase contribution from pipeline output."""
    if not isinstance(phase_result, dict):
        return 0.0
    if phase_result.get("error") or phase_result.get("skipped"):
        return 0.0

    reward = 0.0
    count = phase_result.get("count", 0)
    if isinstance(count, int) and count > 0:
        reward += min(count * 0.1, 3.0)

    if phase_result.get("subdomains"):
        reward += min(len(phase_result["subdomains"]) * 0.05, 2.0)
    if phase_result.get("alive"):
        reward += min(len(phase_result["alive"]) * 0.2, 3.0)
    if phase_result.get("urls"):
        reward += min(len(phase_result["urls"]) * 0.02, 2.0)
    if phase_result.get("secrets") or phase_result.get("secrets_found"):
        reward += 5.0
    if phase_result.get("candidates") or phase_result.get("vulnerable"):
        reward += 4.0
    if phase_result.get("findings"):
        reward += min(len(phase_result["findings"]) * 2.0, 8.0)

    # Bonus if hunt found vulns and this phase is exploit-oriented
    if hunt_findings and phase_name in ("vuln_scanning", "js_secret_scan", "directory_fuzz"):
        reward += 2.0

    return reward


class PhaseQLearner:
    """Q-values per (state, phase) — selects high-yield methodology phases."""

    def __init__(self, alpha: float = 0.15, gamma: float = 0.85, epsilon_start: float = 0.25, epsilon_end: float = 0.05, epsilon_decay: int = 80):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.q_table: dict[str, dict[str, float]] = {}
        self.hunt_count = 0
        self._load()

    def _load(self):
        if PHASE_Q_PATH.exists():
            try:
                data = json.loads(PHASE_Q_PATH.read_text())
                self.q_table = data.get("q_table", {})
                self.hunt_count = data.get("hunt_count", 0)
            except Exception as exc:
                logger.warning("Failed to load phase Q-table: %s", exc)

    def save(self):
        PHASE_Q_PATH.parent.mkdir(parents=True, exist_ok=True)
        PHASE_Q_PATH.write_text(json.dumps({
            "q_table": self.q_table,
            "hunt_count": self.hunt_count,
        }, indent=2))

    def _get_state_q(self, state: str) -> dict[str, float]:
        if state not in self.q_table:
            self.q_table[state] = {p: 0.0 for p in LEARNABLE_PHASES}
        for p in LEARNABLE_PHASES:
            self.q_table[state].setdefault(p, 0.0)
        return self.q_table[state]

    def _epsilon(self) -> float:
        t = self.hunt_count
        return self.epsilon_end + (self.epsilon_start - self.epsilon_end) * math.exp(-t / max(self.epsilon_decay, 1))

    def select_phases(
        self,
        target_type: str = "web",
        tech_stack: list[str] | None = None,
        mode: str = "default",
        max_phases: int = 8,
    ) -> list[str]:
        """
        Return ordered phase list for methodology pipeline.
        mode=full → all phases; mode=default → Q-learned selection.
        """
        if mode == "full":
            return list(FULL_PIPELINE)

        state = encode_phase_state(target_type, tech_stack)
        q = self._get_state_q(state)
        eps = self._epsilon()

        # Always start with passive recon
        selected: list[str] = []
        if "passive_subdomain_enum" in LEARNABLE_PHASES:
            selected.append("passive_subdomain_enum")

        remaining = [p for p in LEARNABLE_PHASES if p not in selected]

        if random.random() < eps:
            random.shuffle(remaining)
            picked = remaining[: max_phases - len(selected)]
        else:
            picked = sorted(remaining, key=lambda p: q.get(p, 0.0), reverse=True)[: max_phases - len(selected)]

        selected.extend(picked)

        # Ensure critical phases if Q-table is cold
        for must in ("alive_host_detection", "url_endpoint_discovery", "vuln_scanning"):
            if must not in selected and must in LEARNABLE_PHASES:
                selected.append(must)

        # Dedupe preserving order
        seen: set[str] = set()
        ordered = []
        for p in selected:
            if p not in seen:
                seen.add(p)
                ordered.append(p)

        logger.info("Phase Q-selection state=%s ε=%.3f phases=%s", state[:8], eps, ordered)
        return ordered

    def update_from_pipeline(
        self,
        target_type: str,
        tech_stack: list[str] | None,
        pipeline_result: dict,
        findings: list[dict],
    ):
        """Update Q-values from methodology pipeline phase results."""
        if not pipeline_result:
            return

        state = encode_phase_state(target_type, tech_stack)
        q = self._get_state_q(state)
        phases = pipeline_result.get("phases") or {}

        total_reward = 0.0
        phase_rewards: dict[str, float] = {}
        for phase_name, phase_data in phases.items():
            r = _phase_reward(phase_name, phase_data, findings)
            phase_rewards[phase_name] = r
            total_reward += r

        # Finding bonus distributed to all ran phases
        if findings:
            finding_bonus = min(len(findings) * 1.5, 10.0)
            for phase_name in phase_rewards:
                phase_rewards[phase_name] += finding_bonus / max(len(phase_rewards), 1)

        for phase_name, reward in phase_rewards.items():
            if phase_name not in q:
                q[phase_name] = 0.0
            old = q[phase_name]
            q[phase_name] = old + self.alpha * (reward - old)

        self.hunt_count += 1
        self.save()
        logger.info(
            "Phase Q-update state=%s total_reward=%.2f findings=%d",
            state[:8], total_reward, len(findings),
        )

    def get_policy_summary(self) -> dict:
        summary = {}
        for state, phases in self.q_table.items():
            ranked = sorted(phases.items(), key=lambda x: x[1], reverse=True)[:5]
            summary[state] = {
                "top_phases": [{"phase": p, "q": round(v, 3)} for p, v in ranked],
            }
        return {
            "states": summary,
            "hunt_count": self.hunt_count,
            "epsilon": round(self._epsilon(), 4),
            "learnable_phases": LEARNABLE_PHASES,
        }


phase_q_learner = PhaseQLearner()
