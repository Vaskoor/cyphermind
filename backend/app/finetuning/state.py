"""Fine-tuning runtime state — enable/disable without code changes."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from app.core.config import PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)

FINETUNING_DIR = PROJECT_ROOT / "data" / "finetuning"
DATASET_DIR = FINETUNING_DIR / "datasets"
STATE_FILE = FINETUNING_DIR / "runtime_state.json"

FINETUNING_DIR.mkdir(parents=True, exist_ok=True)
DATASET_DIR.mkdir(parents=True, exist_ok=True)


def _default_state() -> dict:
    settings = get_settings()
    roles = [r.strip() for r in settings.finetuning_roles.split(",") if r.strip()]
    return {
        "enabled": settings.finetuning_enabled,
        "model_id": settings.finetuning_model_id,
        "base_provider": settings.finetuning_base_provider,
        "api_base": settings.finetuning_api_base or "",
        "api_key": "",  # never persist keys in state file
        "roles": roles,
        "pipeline_auto_export": settings.finetuning_auto_export,
        "last_dataset": None,
        "notes": "",
    }


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            base = _default_state()
            base.update({k: v for k, v in data.items() if k != "api_key"})
            return base
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read finetuning state: %s", exc)
    return _default_state()


def save_state(state: dict) -> dict:
    safe = {k: v for k, v in state.items() if k != "api_key"}
    STATE_FILE.write_text(json.dumps(safe, indent=2), encoding="utf-8")
    return safe


def is_enabled() -> bool:
    """Master check: is fine-tuned model routing active?"""
    return bool(load_state().get("enabled", False))


def is_enabled_for_role(role: str) -> bool:
    if not is_enabled():
        return False
    state = load_state()
    roles = [r.strip().lower() for r in state.get("roles", []) if r.strip()]
    if not roles:
        return False
    return role.lower().strip().replace("-", "_") in roles


def set_enabled(enabled: bool) -> dict:
    state = load_state()
    state["enabled"] = enabled
    return save_state(state)


def update_state(updates: dict) -> dict:
    state = load_state()
    allowed = {
        "enabled", "model_id", "base_provider", "api_base",
        "roles", "pipeline_auto_export", "notes", "last_dataset",
    }
    for k, v in updates.items():
        if k in allowed:
            state[k] = v
    return save_state(state)


def get_model_id() -> str:
    state = load_state()
    settings = get_settings()
    return state.get("model_id") or settings.finetuning_model_id


def get_roles() -> list[str]:
    state = load_state()
    return [r.strip() for r in state.get("roles", []) if r.strip()]
