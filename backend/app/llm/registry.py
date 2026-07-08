"""Provider registry — resolve name/role to configured backend."""
from __future__ import annotations

import os
from typing import Optional

from app.core.config import get_settings
from app.llm.base import DEFAULT_ROLE_MAP, PROVIDER_PRESETS, BaseLLMProvider, LLMError, ProviderConfig
from app.llm.openai_compat import OpenAICompatibleProvider

_provider_cache: dict[str, BaseLLMProvider] = {}


def _first_env(keys: list[str], default: str = "") -> str:
    for k in keys:
        val = os.environ.get(k, "").strip()
        if val:
            return val
    return default


def resolve_provider_config(name: str) -> ProviderConfig:
    """Build ProviderConfig from preset + environment overrides."""
    key = name.lower().strip()
    preset = PROVIDER_PRESETS.get(key)
    if not preset:
        raise LLMError(
            f"Unknown LLM provider '{name}'. "
            f"Available: {', '.join(sorted(PROVIDER_PRESETS))}"
        )

    settings = get_settings()
    api_key = _first_env(preset.get("api_key_env", []))
    api_base = _first_env(preset.get("api_base_env", []), preset["api_base"])
    model = _first_env(preset.get("model_env", []), preset["model"])

    if not api_key:
        env_hint = preset.get("api_key_env", ["LLM_*_API_KEY"])[0]
        raise LLMError(
            f"API key not set for provider '{key}'. "
            f"Add {env_hint}=... to your .env file."
        )

    return ProviderConfig(
        name=key,
        label=preset.get("label", key),
        api_key=api_key,
        api_base=api_base.rstrip("/"),
        model=model,
        timeout_seconds=settings.llm_timeout_seconds,
        supports_tools=preset.get("supports_tools", True),
        extra_headers=dict(preset.get("extra_headers") or {}),
    )


def resolve_role_provider_name(role: str) -> str:
    """Map logical role (bug_bounty, selfplay, …) to provider preset name."""
    settings = get_settings()
    role_key = role.lower().strip().replace("-", "_")

    # Explicit role override: LLM_PROVIDER_BUG_BOUNTY=grok
    role_env = f"LLM_PROVIDER_{role_key.upper()}"
    override = os.environ.get(role_env, "").strip().lower()
    if override:
        return override

    # Fall back to default provider
    default = settings.llm_default_provider.lower()
    return DEFAULT_ROLE_MAP.get(role_key, default)


def get_provider(name: Optional[str] = None) -> BaseLLMProvider:
    """Get or create cached provider instance by preset name."""
    if not name:
        name = get_settings().llm_default_provider
    key = name.lower().strip()

    if key not in _provider_cache:
        config = resolve_provider_config(key)
        _provider_cache[key] = OpenAICompatibleProvider(config)

    return _provider_cache[key]


def get_provider_for_role(role: str = "default") -> BaseLLMProvider:
    """Resolve role → provider name → provider instance. Uses fine-tuned model when enabled."""
    from app.finetuning.state import is_enabled_for_role
    from app.finetuning.provider import get_finetuned_provider

    if is_enabled_for_role(role):
        return get_finetuned_provider()

    provider_name = resolve_role_provider_name(role)
    return get_provider(provider_name)


def list_providers() -> list[dict]:
    """List built-in presets and whether API keys are configured."""
    out = []
    for name, preset in PROVIDER_PRESETS.items():
        try:
            cfg = resolve_provider_config(name)
            configured = bool(cfg.api_key)
        except LLMError:
            configured = False
            cfg = None
        out.append({
            "name": name,
            "label": preset.get("label", name),
            "model": cfg.model if cfg else preset.get("model"),
            "api_base": cfg.api_base if cfg else preset.get("api_base"),
            "configured": configured,
            "api_key_env": preset.get("api_key_env", [])[0],
        })
    return out


def list_role_mappings() -> dict[str, str]:
    """Show which provider each role resolves to."""
    from app.finetuning.state import is_enabled_for_role

    roles = set(DEFAULT_ROLE_MAP) | {"default"}
    settings = get_settings()
    roles.add(settings.llm_default_provider)
    out = {}
    for role in sorted(roles):
        if is_enabled_for_role(role):
            out[role] = "finetuned"
        else:
            out[role] = resolve_role_provider_name(role)
    return out


def clear_provider_cache():
    """Reset cached providers (useful after .env change in tests)."""
    _provider_cache.clear()
    try:
        from app.finetuning.provider import clear_finetuned_cache
        clear_finetuned_cache()
    except ImportError:
        pass
