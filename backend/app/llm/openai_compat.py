"""OpenAI-compatible chat completions (NVIDIA, Grok, OpenAI, OpenRouter, Ollama, …)."""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.llm.base import BaseLLMProvider, LLMError

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    """Works with any OpenAI-style /chat/completions API."""

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
        cfg = self.config
        payload: dict[str, Any] = {
            "model": model or cfg.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
        }
        if tools and cfg.supports_tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            **cfg.extra_headers,
        }
        url = f"{cfg.api_base}/chat/completions"

        async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:800]
                if tools and exc.response.status_code in (400, 422):
                    logger.warning(
                        "%s rejected tools payload, retrying without tools",
                        cfg.label,
                    )
                    return await self.chat_completion_raw(
                        messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        model=model,
                        tools=None,
                    )
                raise LLMError(
                    f"{cfg.label} API error {exc.response.status_code}: {detail}"
                ) from exc
            except httpx.RequestError as exc:
                raise LLMError(f"{cfg.label} API unreachable: {exc}") from exc

        try:
            return data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected {cfg.label} response: {data}") from exc
