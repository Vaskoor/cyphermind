"""
Q-Learning Orchestrator
=======================
Pseudocode:
  State:  hash(target_type + tech_stack + num_ports + code_language)
  Action: bitmask of 4 agents (16 combinations, 0001..1111)
  Reward: (vuln_count × avg_severity_score × novelty_bonus) / time_seconds
  Update: Q(s,a) ← Q(s,a) + α[r + γ·max_a'Q(s',a') - Q(s,a)]
  Policy: ε-greedy, ε decays 0.3 → 0.05 over 100 engagements

Complexity: O(1) per update, O(16) per action selection
"""
from __future__ import annotations
import hashlib
import json
import math
import random
import time
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

AGENT_NAMES = ["ReconAgent", "SASTAgent", "ExploitAgent", "PostExploitAgent"]
N_AGENTS = len(AGENT_NAMES)
N_ACTIONS = 2 ** N_AGENTS  # 16

from app.core.config import PROJECT_ROOT

Q_TABLE_PATH = PROJECT_ROOT / "data" / "q_table.json"

def _severity_to_score(severity: str) -> float:
    return {"critical": 10, "high": 7, "medium": 4, "low": 1, "info": 0.1}.get(severity.lower(), 1)

def encode_state(target_type: str, tech_stack: list[str], num_ports: int, code_language: str) -> str:
    """Discretize environment into a hashable state string."""
    key = f"{target_type}|{','.join(sorted(tech_stack))}|{min(num_ports//10, 10)}|{code_language}"
    return hashlib.md5(key.encode()).hexdigest()[:16]

def action_to_agents(action: int) -> list[str]:
    """Convert bitmask action to list of agent names."""
    return [AGENT_NAMES[i] for i in range(N_AGENTS) if action & (1 << i)]

def agents_to_action(agents: list[str]) -> int:
    """Convert list of agent names to bitmask action."""
    action = 0
    for name in agents:
        if name in AGENT_NAMES:
            action |= 1 << AGENT_NAMES.index(name)
    return action

def compute_reward(
    vuln_count: int,
    severity_scores: list[float],
    novel_count: int,
    time_seconds: float,
) -> float:
    """
    R = (vuln_count × avg_severity × novelty_bonus) / time_seconds
    novelty_bonus = 1 + 0.5 × (novel_count / max(vuln_count, 1))
    """
    if time_seconds <= 0:
        time_seconds = 1.0
    avg_severity = sum(severity_scores) / len(severity_scores) if severity_scores else 0
    novelty_bonus = 1 + 0.5 * (novel_count / max(vuln_count, 1))
    return (vuln_count * avg_severity * novelty_bonus) / time_seconds

class QLearningOrchestrator:
    """Tabular Q-learning for multi-agent selection."""

    def __init__(
        self,
        alpha: float = 0.1,
        gamma: float = 0.9,
        epsilon_start: float = 0.3,
        epsilon_end: float = 0.05,
        epsilon_decay: int = 100,
    ):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay

        self.q_table: dict[str, list[float]] = {}
        self.engagement_count = 0
        self._load()

    # ── Persistence ──────────────────────────────────────────────────────────
    def _load(self):
        if Q_TABLE_PATH.exists():
            try:
                data = json.loads(Q_TABLE_PATH.read_text())
                self.q_table = data.get("q_table", {})
                self.engagement_count = data.get("engagement_count", 0)
                logger.info(f"Q-table loaded: {len(self.q_table)} states, {self.engagement_count} engagements")
            except Exception as e:
                logger.warning(f"Failed to load Q-table: {e}")

    def save(self):
        Q_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        Q_TABLE_PATH.write_text(json.dumps({
            "q_table": self.q_table,
            "engagement_count": self.engagement_count,
        }, indent=2))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_q(self, state: str) -> list[float]:
        if state not in self.q_table:
            self.q_table[state] = [0.0] * N_ACTIONS
        return self.q_table[state]

    def _epsilon(self) -> float:
        """Decaying epsilon: ε = ε_end + (ε_start - ε_end) × exp(-t / decay)"""
        t = self.engagement_count
        return self.epsilon_end + (self.epsilon_start - self.epsilon_end) * math.exp(
            -t / max(self.epsilon_decay, 1)
        )

    # ── Core RL API ───────────────────────────────────────────────────────────
    def select_action(self, state: str) -> tuple[int, list[str]]:
        """
        ε-greedy action selection.
        Returns (action_bitmask, [agent_names])
        """
        eps = self._epsilon()
        if random.random() < eps:
            # Exploration: random action (at least 1 agent)
            action = random.randint(1, N_ACTIONS - 1)
            logger.debug(f"Exploring: action={action}, ε={eps:.3f}")
        else:
            # Exploitation: greedy best action
            q_vals = self._get_q(state)
            # Exclude action=0 (no agents)
            action = max(range(1, N_ACTIONS), key=lambda a: q_vals[a])
            logger.debug(f"Exploiting: action={action}, Q={q_vals[action]:.3f}")

        return action, action_to_agents(action)

    def update(
        self,
        state: str,
        action: int,
        reward: float,
        next_state: str,
        done: bool = True,
    ):
        """
        Q-learning update rule:
        Q(s,a) ← Q(s,a) + α[r + γ·max_a'Q(s',a') - Q(s,a)]
        """
        q = self._get_q(state)
        next_q = self._get_q(next_state)
        max_next = max(next_q) if not done else 0.0

        old_val = q[action]
        q[action] = old_val + self.alpha * (reward + self.gamma * max_next - old_val)

        self.engagement_count += 1
        self.save()
        logger.info(
            f"Q-update: state={state[:8]}… action={action} "
            f"Q {old_val:.3f}→{q[action]:.3f} reward={reward:.3f}"
        )

    def get_policy_summary(self) -> dict:
        """Return human-readable policy for dashboard."""
        summary = {}
        for state, q_vals in self.q_table.items():
            best_action = max(range(1, N_ACTIONS), key=lambda a: q_vals[a])
            summary[state] = {
                "best_action": best_action,
                "best_agents": action_to_agents(best_action),
                "q_value": q_vals[best_action],
            }
        return {
            "states": summary,
            "engagement_count": self.engagement_count,
            "epsilon": self._epsilon(),
        }

# Singleton
q_orchestrator = QLearningOrchestrator()
