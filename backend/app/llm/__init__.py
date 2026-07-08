"""LLM provider layer — swap APIs via config without touching call sites."""
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
