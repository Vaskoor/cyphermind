"""CypherMind FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import init_db
from app.api.routers import (
    agents,
    auth,
    bug_bounty,
    chat,
    dashboard,
    engagements,
    findings,
    knowledge,
    learning,
    finetuning,
    reports,
    selfplay,
    settings,
    tools,
    wordlists,
    ws,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting CypherMind backend...")
    await init_db()
    _seed_methodology_kb()
    yield
    logger.info("Shutting down CypherMind backend.")


def _seed_methodology_kb():
    """Ingest bug bounty methodology doc into RAG for enrich_finding_with_rag."""
    from app.core.config import PROJECT_ROOT
    from app.services.rag_service import rag_service

    doc = PROJECT_ROOT / "data" / "knowledge" / "bug_bounty_methodology.md"
    if not doc.exists():
        return
    try:
        content = doc.read_text(encoding="utf-8")
        rag_service.add_chunk(
            chunk_id="bug_bounty_methodology_2026",
            content=content,
            metadata={"source": "bug_bounty_methodology.md", "type": "methodology"},
        )
        logger.info("Seeded bug bounty methodology into knowledge base")
    except Exception as exc:
        logger.warning("Could not seed methodology KB: %s", exc)


app = FastAPI(
    title="CypherMind API",
    description="Self-Learning AI Penetration Testing Copilot",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in [
    auth.router,
    bug_bounty.router,
    engagements.router,
    agents.router,
    chat.router,
    knowledge.router,
    selfplay.router,
    reports.router,
    learning.router,
    finetuning.router,
    dashboard.router,
    findings.router,
    settings.router,
    tools.router,
    wordlists.router,
]:
    app.include_router(router, prefix="/api/v1")

app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "CypherMind"}
