"""Unit tests for Q-learning orchestrator."""
from app.learning.q_learning import (
    QLearningOrchestrator,
    encode_state,
    action_to_agents,
    agents_to_action,
    compute_reward,
)


def test_encode_state_deterministic():
    s1 = encode_state("web", ["python", "flask"], 5, "python")
    s2 = encode_state("web", ["python", "flask"], 5, "python")
    assert s1 == s2


def test_action_roundtrip():
    agents = ["ReconAgent", "SASTAgent"]
    action = agents_to_action(agents)
    recovered = action_to_agents(action)
    assert set(recovered) == set(agents)


def test_compute_reward_positive():
    r = compute_reward(5, [7.0, 10.0, 4.0], 2, 60.0)
    assert r > 0
