"""Tests for fine-tuning module."""
import pytest

from app.finetuning.state import (
    STATE_FILE,
    is_enabled,
    is_enabled_for_role,
    load_state,
    save_state,
    set_enabled,
)
from app.llm.registry import clear_provider_cache, list_role_mappings


@pytest.fixture(autouse=True)
def reset_finetuning_state(tmp_path, monkeypatch):
  backup = STATE_FILE.read_text(encoding="utf-8") if STATE_FILE.exists() else None
  monkeypatch.setenv("FINETUNING_ENABLED", "false")
  monkeypatch.setenv("FINETUNING_ROLES", "bug_bounty,agent")
  clear_provider_cache()
  if STATE_FILE.exists():
    STATE_FILE.unlink()
  yield
  clear_provider_cache()
  if backup:
    STATE_FILE.write_text(backup, encoding="utf-8")
  elif STATE_FILE.exists():
    STATE_FILE.unlink()


def test_disabled_by_default():
    assert is_enabled() is False
    assert is_enabled_for_role("bug_bounty") is False


def test_enable_for_role(monkeypatch):
    monkeypatch.setenv("FINETUNING_MODEL_ID", "ft:test-model")
    save_state({
        "enabled": True,
        "model_id": "ft:test-model",
        "roles": ["bug_bounty"],
        "base_provider": "nvidia",
    })
    clear_provider_cache()
    assert is_enabled() is True
    assert is_enabled_for_role("bug_bounty") is True
    assert is_enabled_for_role("selfplay") is False


def test_toggle():
    set_enabled(True)
    assert load_state()["enabled"] is True
    set_enabled(False)
    assert load_state()["enabled"] is False


def test_role_mapping_shows_finetuned_when_enabled(monkeypatch):
    monkeypatch.setenv("FINETUNING_MODEL_ID", "ft:test")
    save_state({"enabled": True, "model_id": "ft:test", "roles": ["bug_bounty"]})
    clear_provider_cache()
    mappings = list_role_mappings()
    assert mappings.get("bug_bounty") == "finetuned"
