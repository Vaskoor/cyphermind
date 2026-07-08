"""Fine-tuning pipeline orchestration."""
from __future__ import annotations

import logging
from typing import Optional

from app.finetuning import dataset, state
from app.finetuning.provider import clear_finetuned_cache, get_finetuned_provider, resolve_finetuned_config
from app.llm.registry import clear_provider_cache

logger = logging.getLogger(__name__)


async def get_status() -> dict:
    """Full fine-tuning module status."""
    st = state.load_state()
    cfg_ok = False
    cfg_error = None
    try:
        cfg = resolve_finetuned_config()
        cfg_ok = bool(cfg.model and cfg.api_key)
    except Exception as exc:
        cfg_error = str(exc)

    return {
        "enabled": state.is_enabled(),
        "configured": cfg_ok,
        "config_error": cfg_error,
        "model_id": state.get_model_id(),
        "roles": state.get_roles(),
        "base_provider": st.get("base_provider"),
        "api_base": st.get("api_base") or "(inherits from base provider)",
        "pipeline_auto_export": st.get("pipeline_auto_export", False),
        "last_dataset": st.get("last_dataset"),
        "datasets": dataset.list_datasets(),
        "notes": st.get("notes", ""),
        "usage": (
            "When enabled, configured roles route to your fine-tuned model instead of base LLM. "
            "Disable anytime to fall back to Kimi/Grok/etc."
        ),
    }


async def build_dataset(**kwargs) -> dict:
    meta = await dataset.build_dataset(**kwargs)
    state.update_state({"last_dataset": meta})
    return meta


async def toggle(enabled: bool) -> dict:
    result = state.set_enabled(enabled)
    clear_finetuned_cache()
    clear_provider_cache()
    logger.info("Fine-tuning %s", "enabled" if enabled else "disabled")
    return {"enabled": result["enabled"], "message": f"Fine-tuning {'enabled' if enabled else 'disabled'}"}


async def update_config(updates: dict) -> dict:
    result = state.update_state(updates)
    clear_finetuned_cache()
    clear_provider_cache()
    return result


async def health_check() -> dict:
    if not state.is_enabled():
        return {"online": False, "enabled": False, "error": "Fine-tuning is disabled"}
    try:
        provider = get_finetuned_provider()
        reply = await provider.chat_completion(
            [{"role": "user", "content": "Reply with exactly: ok"}],
            temperature=0,
            max_tokens=8,
        )
        return {
            "online": True,
            "enabled": True,
            "provider": "finetuned",
            "model": provider.config.model,
            "api_base": provider.config.api_base,
            "test_reply": reply.strip()[:32],
        }
    except Exception as exc:
        return {"online": False, "enabled": True, "error": str(exc)}


async def maybe_auto_export():
    """Called after hunts if auto-export is on."""
    st = state.load_state()
    if not st.get("pipeline_auto_export"):
        return None
    return await build_dataset(max_samples=500)
