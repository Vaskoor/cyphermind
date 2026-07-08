"""OpenAI-compatible tool registry and dispatcher."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., Awaitable[Any]]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    category: str = "general"

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        category: str = "general",
    ):
        def decorator(fn: ToolHandler):
            self._tools[name] = Tool(name, description, parameters, fn, category)
            return fn
        return decorator

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self, category: str | None = None) -> list[Tool]:
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def openai_schemas(self, names: list[str] | None = None) -> list[dict]:
        tools = self._tools.values()
        if names:
            tools = [self._tools[n] for n in names if n in self._tools]
        return [t.to_openai_schema() for t in tools]

    async def execute(self, name: str, arguments: dict | str, context: dict | None = None) -> dict:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except json.JSONDecodeError:
                arguments = {"raw": arguments}

        ctx = context or {}
        try:
            result = await tool.handler(**arguments, _context=ctx)
            return {"tool": name, "success": True, "result": result}
        except TypeError as exc:
            # Retry without _context if handler doesn't accept it
            try:
                result = await tool.handler(**arguments)
                return {"tool": name, "success": True, "result": result}
            except Exception as inner:
                logger.exception("Tool %s failed", name)
                return {"tool": name, "success": False, "error": str(inner)}
        except Exception as exc:
            logger.exception("Tool %s failed", name)
            return {"tool": name, "success": False, "error": str(exc)}


tool_registry = ToolRegistry()
