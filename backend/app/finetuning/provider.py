"""Fine-tuned model provider — separate from base LLM presets."""
from __future__ import annotations

import os
from typing import Optional

from app.core.config import get_settings
from app.finetuning.state import get_model_id, load_state
from app.llm.base import LLMError, ProviderConfig
from app.llm.openai_compat import OpenAICompatibleProvider
from app.llm.registry import _first_env, resolve_provider_config

_finetuned_provider: Optional[OpenAICompatibleProvider] = None


def resolve_finetuned_config() -> ProviderConfig:
    """Build ProviderConfig for the fine-tuned model endpoint."""
    settings = get_settings()
    state = load_state()
    model_id = get_model_id()

    if not model_id:
        raise LLMError(
            "FINETUNING_MODEL_ID is not set. "
            "Add your fine-tuned model ID to .env or via POST /api/v1/finetuning/config"
        )

    base_provider = state.get("base_provider") or settings.finetuning_base_provider
    base_cfg = resolve_provider_config(base_provider)

    api_key = (
        _first_env(["FINETUNING_API_KEY", "LLM_FINETUNING_API_KEY"])
        or base_cfg.api_key
    )
    api_base = (
        state.get("api_base")
        or settings.finetuning_api_base
        or base_cfg.api_base
    ).rstrip("/")

    if not api_key:
        raise LLMError("No API key for fine-tuned model. Set FINETUNING_API_KEY or base provider key.")

    return ProviderConfig(
        name="finetuned",
        label=f"Fine-tuned ({model_id[:40]})",
        api_key=api_key,
        api_base=api_base,
        model=model_id,
        timeout_seconds=settings.llm_timeout_seconds,
        supports_tools=settings.finetuning_supports_tools,
        extra_headers=dict(base_cfg.extra_headers),
    )


def get_finetuned_provider() -> OpenAICompatibleProvider:
    global _finetuned_provider
    config = resolve_finetuned_config()
    # Refresh if model_id changed
    if _finetuned_provider is None or _finetuned_provider.config.model != config.model:
        _finetuned_provider = OpenAICompatibleProvider(config)
    return _finetuned_provider


def clear_finetuned_cache():
    global _finetuned_provider
    _finetuned_provider = None
