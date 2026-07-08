"""Tests for learning systems (no LLM fine-tuning)."""
from app.learning.phase_q_learning import (
    encode_phase_state,
    phase_q_learner,
    _phase_reward,
)
from app.services.attack_memory_service import format_attack_context


def test_phase_reward_secrets():
    r = _phase_reward("js_secret_scan", {"secrets_found": 2, "count": 2}, [])
    assert r >= 5.0


def test_phase_q_select_phases():
    state = encode_phase_state("web", ["react"])
    phases = phase_q_learner.select_phases("web", ["react"], mode="default")
    assert "passive_subdomain_enum" in phases
    assert len(phases) >= 4


def test_phase_q_update():
    before = dict(phase_q_learner.q_table)
    phase_q_learner.update_from_pipeline(
        "web",
        ["api"],
        {
            "phases": {
                "js_secret_scan": {"secrets_found": 1, "count": 1},
                "passive_subdomain_enum": {"count": 10, "subdomains": ["a.example.com"]},
            }
        },
        [{"title": "XSS", "severity": "high"}],
    )
    assert phase_q_learner.hunt_count >= 1


def test_format_attack_context_empty():
    assert format_attack_context([], []) == ""
