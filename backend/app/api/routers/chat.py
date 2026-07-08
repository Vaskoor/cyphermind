"""RAG + tool-augmented chat router."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.agent_loop import run_agent_loop
from app.services.rag_service import rag_service

router = APIRouter(prefix="/chat", tags=["chat"])

CHAT_SYSTEM = """You are CypherMind, an expert bug bounty and penetration testing copilot.
Use tools when you need current CVE info, web search results, HTTP probing, or knowledge base lookups.
Be concise, technical, and cite CWE/CVE IDs when relevant."""


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[list[dict]] = None
    use_tools: bool = True
    scope_domains: list[str] = []


@router.post("")
async def chat(body: ChatRequest):
    if body.use_tools:
        history_note = ""
        if body.history:
            history_note = "\n\nPrior conversation:\n" + "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')[:300]}"
                for m in body.history[-4:]
            )
        result = await run_agent_loop(
            body.message + history_note,
            system_prompt=CHAT_SYSTEM,
            context={"scope_domains": body.scope_domains},
            max_iterations=8,
            temperature=0.5,
            llm_role="chat",
        )
        chunks = rag_service.retrieve(body.message, top_k=3)
        return {
            "answer": result.final_answer,
            "citations": [{"content": c.content[:300], "score": c.score} for c in chunks],
            "tool_calls": result.tool_calls_made,
            "findings": result.findings,
            "iterations": result.iterations,
        }

    answer = await rag_service.query_with_llm(body.message, body.history)
    chunks = rag_service.retrieve(body.message, top_k=3)
    return {
        "answer": answer,
        "citations": [{"content": c.content[:300], "score": c.score} for c in chunks],
        "tool_calls": [],
    }
