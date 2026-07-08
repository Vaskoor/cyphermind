"""LLM provider base types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


class LLMError(Exception):
    """Raised when an LLM API call fails."""


@dataclass(frozen=True)
class ProviderConfig:
    """Resolved credentials + endpoint for one provider."""

    name: str
    label: str
    api_key: str
    api_base: str
    model: str
    timeout_seconds: int = 180
    supports_tools: bool = True
    extra_headers: dict[str, str] = field(default_factory=dict)


# Built-in provider presets — override any field via .env (see registry.py)
PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "nvidia": {
        "label": "NVIDIA NIM",
        "api_base": "https://integrate.api.nvidia.com/v1",
        "model": "moonshotai/kimi-k2.6",
        "api_key_env": ["LLM_NVIDIA_API_KEY", "NVIDIA_API_KEY"],
        "api_base_env": ["LLM_NVIDIA_API_BASE", "NVIDIA_API_BASE"],
        "model_env": ["LLM_NVIDIA_MODEL", "LLM_MODEL"],
    },
    "kimi": {
        "label": "Kimi (NVIDIA NIM)",
        "api_base": "https://integrate.api.nvidia.com/v1",
        "model": "moonshotai/kimi-k2.6",
        "api_key_env": ["LLM_KIMI_API_KEY", "NVIDIA_API_KEY"],
        "api_base_env": ["LLM_KIMI_API_BASE", "NVIDIA_API_BASE"],
        "model_env": ["LLM_KIMI_MODEL", "LLM_MODEL"],
    },
    "grok": {
        "label": "xAI Grok",
        "api_base": "https://api.x.ai/v1",
        "model": "grok-2-latest",
        "api_key_env": ["LLM_GROK_API_KEY", "GROK_API_KEY", "XAI_API_KEY"],
        "api_base_env": ["LLM_GROK_API_BASE", "GROK_API_BASE"],
        "model_env": ["LLM_GROK_MODEL", "GROK_MODEL"],
    },
    "openai": {
        "label": "OpenAI",
        "api_base": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key_env": ["LLM_OPENAI_API_KEY", "OPENAI_API_KEY"],
        "api_base_env": ["LLM_OPENAI_API_BASE", "OPENAI_API_BASE"],
        "model_env": ["LLM_OPENAI_MODEL"],
    },
    "openrouter": {
        "label": "OpenRouter",
        "api_base": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-sonnet-4",
        "api_key_env": ["LLM_OPENROUTER_API_KEY", "OPENROUTER_API_KEY"],
        "api_base_env": ["LLM_OPENROUTER_API_BASE", "OPENROUTER_API_BASE"],
        "model_env": ["LLM_OPENROUTER_MODEL"],
        "extra_headers": {"HTTP-Referer": "https://cyphermind.local", "X-Title": "CypherMind"},
    },
    "custom": {
        "label": "Custom OpenAI-compatible",
        "api_base": "http://localhost:11434/v1",
        "model": "llama3",
        "api_key_env": ["LLM_CUSTOM_API_KEY"],
        "api_base_env": ["LLM_CUSTOM_API_BASE"],
        "model_env": ["LLM_CUSTOM_MODEL"],
    },
}

# Logical roles → provider name (overridable in .env)
DEFAULT_ROLE_MAP: dict[str, str] = {
    "default": "nvidia",
    "bug_bounty": "nvidia",
    "agent": "nvidia",
    "chat": "nvidia",
    "rag": "nvidia",
    "selfplay": "nvidia",
    "selfplay_red": "nvidia",
    "selfplay_blue": "nvidia",
}


class BaseLLMProvider(ABC):
    """Abstract LLM backend."""

    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    async def chat_completion_raw(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 1.0,
        model: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        tool_choice: str | dict = "auto",
    ) -> dict[str, Any]:
        ...

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        **kwargs,
    ) -> str:
        msg = await self.chat_completion_raw(messages, **kwargs)
        return msg.get("content") or ""
