"""
Policy selector — blends Q-learning with Bradley-Terry human preferences.
No LLM fine-tuning; improves agent combo selection over time.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.learning.bradley_terry import fit_bradley_terry
from app.learning.q_learning import (
    AGENT_NAMES,
    N_ACTIONS,
    action_to_agents,
    agents_to_action,
    encode_state,
    q_orchestrator,
)

logger = logging.getLogger(__name__)

BUG_BOUNTY_AGENTS = ["BugBountyAgent"]


def _combo_key(agents: list[str]) -> str:
    return "+".join(sorted(agents))


async def load_bt_scores(db) -> dict[str, float]:
    """Load Bradley-Terry scores from preference pairs in DB."""
    from sqlalchemy import select
    from app.models.learning import PreferencePair

    result = await db.execute(select(PreferencePair))
    pairs = result.scalars().all()
    bt_pairs = [
        (p.agent_combo_a, p.agent_combo_b, p.winner)
        for p in pairs
        if p.agent_combo_a and p.agent_combo_b
    ]
    if not bt_pairs:
        return {}
    return fit_bradley_terry(bt_pairs)


def select_agents(
    target_type: str,
    tech_stack: list[str] | None,
    num_ports: int,
    code_language: str = "python",
    bt_scores: dict[str, float] | None = None,
    mode: str = "standard",
) -> tuple[list[str], int, str]:
    """
    Select agent combination using Q-learning + optional BT boost.
    Returns (agent_names, action_bitmask, selection_reason).
    """
    if mode in ("bug_bounty", "autonomous"):
        return BUG_BOUNTY_AGENTS, 0, "bug_bounty_mode"

    state = encode_state(target_type, tech_stack or [], num_ports, code_language)
    eps = q_orchestrator._epsilon()

    # ε-greedy base selection from Q-table
    action, agents = q_orchestrator.select_action(state)

    # If exploiting and BT scores exist, pick best combo among top Q actions
    if bt_scores and eps < 0.15:
        q_vals = q_orchestrator._get_q(state)
        top_actions = sorted(range(1, N_ACTIONS), key=lambda a: q_vals[a], reverse=True)[:5]
        best_action = action
        best_score = -1.0
        for a in top_actions:
            combo = _combo_key(action_to_agents(a))
            bt = bt_scores.get(combo, 0.5)
            blended = q_vals[a] * 0.6 + bt * 10 * 0.4
            if blended > best_score:
                best_score = blended
                best_action = a
        agents = action_to_agents(best_action)
        action = best_action
        reason = f"q_bt_blend(q={q_vals[action]:.2f}, bt={bt_scores.get(_combo_key(agents), 0):.2f})"
        return agents, action, reason

    reason = "explore" if eps > 0.2 else f"q_greedy(action={action})"
    return agents, action, reason


def record_engagement_outcome(
    target_type: str,
    tech_stack: list[str] | None,
    num_ports: int,
    agents: list[str],
    findings: list[dict],
    novel_count: int,
    time_seconds: float,
    code_language: str = "python",
):
    """Update Q-table after engagement (wrapper for orchestrator)."""
    from app.learning.q_learning import compute_reward

    state = encode_state(target_type, tech_stack or [], num_ports, code_language)
    action = agents_to_action(agents)
    severity_scores = [
        {"critical": 10, "high": 7, "medium": 4, "low": 1}.get(f.get("severity", "low"), 1)
        for f in findings
    ]
    reward = compute_reward(len(findings), severity_scores, novel_count, time_seconds)
    q_orchestrator.update(state, action, reward, state)
