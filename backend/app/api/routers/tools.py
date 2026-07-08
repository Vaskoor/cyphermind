"""Tool listing and direct invocation API."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import app.tools.bootstrap  # noqa: F401 — register tools
from app.tools.registry import tool_registry

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolInvokeRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    scope_domains: list[str] = Field(default_factory=list)


@router.get("")
async def list_tools(category: Optional[str] = None):
    tools = tool_registry.list_tools(category)
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "parameters": t.parameters,
            }
            for t in tools
        ],
        "count": len(tools),
    }


@router.post("/invoke")
async def invoke_tool(body: ToolInvokeRequest):
    tool = tool_registry.get(body.tool_name)
    if not tool:
        raise HTTPException(404, f"Tool not found: {body.tool_name}")

    ctx = {"scope_domains": body.scope_domains, "findings_collector": []}
    result = await tool_registry.execute(body.tool_name, body.arguments, ctx)
    return result
