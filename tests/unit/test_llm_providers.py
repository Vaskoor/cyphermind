"""Tests for pluggable LLM provider layer."""
import os
import pytest

from app.llm.base import LLMError
from app.llm.registry import (
    clear_provider_cache,
    list_providers,
    resolve_provider_config,
    resolve_role_provider_name,
)


def test_list_providers_includes_presets():
    providers = list_providers()
    names = {p["name"] for p in providers}
    assert "nvidia" in names
    assert "grok" in names
    assert "openai" in names


def test_resolve_role_default():
    name = resolve_role_provider_name("bug_bounty")
    assert name in ("nvidia", "kimi", "grok", "openai", "openrouter", "custom")


def test_resolve_role_env_override(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER_SELFPLAY", "grok")
    clear_provider_cache()
    assert resolve_role_provider_name("selfplay") == "grok"


def test_unknown_provider_raises():
    with pytest.raises(LLMError, match="Unknown LLM provider"):
        resolve_provider_config("not_a_real_provider")


def test_nvidia_config_from_env(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key-123")
    monkeypatch.setenv("NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setenv("LLM_MODEL", "moonshotai/kimi-k2.6")
    clear_provider_cache()
    cfg = resolve_provider_config("nvidia")
    assert cfg.api_key == "test-key-123"
    assert cfg.model == "moonshotai/kimi-k2.6"
    assert "nvidia.com" in cfg.api_base
