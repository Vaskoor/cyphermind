"""
LLM service — backward-compatible re-export of the provider layer.

Swap providers via .env only:
  LLM_DEFAULT_PROVIDER=nvidia
  LLM_PROVIDER_BUG_BOUNTY=nvidia
  LLM_PROVIDER_SELFPLAY=grok
  NVIDIA_API_KEY=...
  GROK_API_KEY=...
"""
from app.llm.facade import (
    LLMError,
    chat_completion,
    chat_completion_for_role,
    chat_completion_raw,
    check_llm_health,
    check_provider_health,
    list_providers,
    parse_react_tool_calls,
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
