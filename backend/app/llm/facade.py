"""Public LLM facade — all app code imports from here or app.services.llm_service."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.core.config import get_settings
from app.llm.base import LLMError
from app.llm.registry import (
    get_provider,
    get_provider_for_role,
    list_providers,
    list_role_mappings,
    resolve_role_provider_name,
)

__all__ = [
    "LLMError",
    "chat_completion",
    "chat_completion_raw",
    "chat_completion_for_role",
    "check_llm_health",
    "check_provider_health",
    "list_providers",
    "parse_react_tool_calls",
]


async def chat_completion_raw(
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    top_p: float = 1.0,
    model: Optional[str] = None,
    tools: Optional[list[dict]] = None,
    tool_choice: str | dict = "auto",
    provider: Optional[str] = None,
    role: str = "default",
) -> dict[str, Any]:
    """
    Return full OpenAI-compatible message object.

    Args:
        provider: Preset name (nvidia, grok, kimi, openai, …). Overrides role.
        role: Logical role (bug_bounty, selfplay, rag, chat) → mapped via LLM_PROVIDER_* env.
    """
    backend = get_provider(provider) if provider else get_provider_for_role(role)
    return await backend.chat_completion_raw(
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        model=model,
        tools=tools,
        tool_choice=tool_choice,
    )


async def chat_completion(
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    top_p: float = 1.0,
    model: Optional[str] = None,
    tools: Optional[list[dict]] = None,
    provider: Optional[str] = None,
    role: str = "default",
) -> str:
    msg = await chat_completion_raw(
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        model=model,
        tools=tools,
        provider=provider,
        role=role,
    )
    return msg.get("content") or ""


async def chat_completion_for_role(role: str, messages: list[dict[str, Any]], **kwargs) -> str:
    """Shortcut: chat completion for a named role."""
    return await chat_completion(messages, role=role, **kwargs)


def parse_react_tool_calls(content: str) -> list[dict]:
    """Fallback parser for text-based tool calls from models without native tool support."""
    calls = []
    for block in re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL):
        try:
            obj = json.loads(block)
            if "tool" in obj:
                calls.append({"name": obj["tool"], "arguments": obj.get("arguments", {})})
        except json.JSONDecodeError:
            continue
    tool_match = re.search(r"TOOL:\s*(\w+)\s+ARGS:\s*(\{.*\})", content, re.DOTALL)
    if tool_match:
        try:
            calls.append({
                "name": tool_match.group(1),
                "arguments": json.loads(tool_match.group(2)),
            })
        except json.JSONDecodeError:
            pass
    return calls


async def check_provider_health(provider_name: Optional[str] = None) -> dict:
    """Health check for a specific provider or the default."""
    settings = get_settings()
    name = provider_name or settings.llm_default_provider
    try:
        backend = get_provider(name)
        reply = await backend.chat_completion(
            [{"role": "user", "content": "Reply with exactly: ok"}],
            temperature=0,
            max_tokens=8,
        )
        search_backend = "google" if settings.google_api_key else "duckduckgo"
        return {
            "online": True,
            "provider": backend.name,
            "label": backend.config.label,
            "models": [backend.config.model],
            "api_base": backend.config.api_base,
            "test_reply": reply.strip()[:32],
            "web_search_backend": search_backend,
            "tools_enabled": backend.config.supports_tools,
        }
    except LLMError as exc:
        return {
            "online": False,
            "provider": name,
            "models": [],
            "error": str(exc),
        }


async def check_llm_health() -> dict:
    """Health check for default provider + role mappings + fine-tuning status."""
    health = await check_provider_health()
    health["role_mappings"] = list_role_mappings()
    health["available_providers"] = [
        p["name"] for p in list_providers() if p["configured"]
    ]
    try:
        from app.finetuning.pipeline import get_status
        health["finetuning"] = await get_status()
    except Exception:
        health["finetuning"] = {"enabled": False}
    return health
