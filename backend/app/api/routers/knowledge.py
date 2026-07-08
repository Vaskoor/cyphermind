"""Knowledge base ingestion and query router."""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
import tempfile, shutil, uuid
from pathlib import Path
from app.services.rag_service import rag_service
from app.utils.ast_chunker import chunk_file
from app.utils.taint_graph import TaintGraph

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

@router.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    """Upload and chunk a code file into the knowledge base."""
    suffix = Path(file.filename or "upload.py").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    chunks_added = 0
    for chunk in chunk_file(tmp_path):
        chunk_id = str(uuid.uuid4())
        rag_service.add_chunk(
            chunk_id=chunk_id,
            content=chunk.content,
            metadata={
                "source": file.filename or "",
                "language": chunk.language,
                "function_name": chunk.function_name,
                "line_start": chunk.line_start,
                "line_end": chunk.line_end,
            }
        )
        chunks_added += 1

    Path(tmp_path).unlink(missing_ok=True)
    return {"status": "ok", "chunks_added": chunks_added}

@router.post("/query")
async def query_kb(body: QueryRequest):
    results = rag_service.retrieve(body.query, top_k=body.top_k)
    return {"results": [{"content": r.content[:500], "score": r.score, "source": r.source} for r in results]}

@router.post("/analyze-taint")
async def analyze_taint(file: UploadFile = File(...)):
    content = (await file.read()).decode(errors="replace")
    graph = TaintGraph()
    graph.analyze_file(file.filename or "upload", content)
    paths = graph.find_vulnerable_paths()
    return {
        "graph": graph.to_dict(),
        "vulnerable_paths": [
            {
                "source": p.source.label,
                "sink": p.sink.label,
                "has_sanitizer": p.has_sanitizer,
                "confidence": p.confidence,
                "vuln_type": p.vuln_type,
            }
            for p in paths[:20]
        ]
    }
