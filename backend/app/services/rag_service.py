"""
Hybrid RAG Retrieval Service
============================
Pseudocode:
  1. Embed query with local sentence-transformer
  2. Vector search in ChromaDB  (k=20)
  3. BM25 keyword search over in-memory corpus (k=20)
  4. Reciprocal Rank Fusion to merge ranked lists
  5. Cross-encoder re-ranking (top 5)
  6. Return top_k results with citations

Complexity: O(n) BM25 build, O(k log n) retrieval
"""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional
import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

RRF_K = 60  # RRF constant

@dataclass
class RetrievedChunk:
    content: str
    source: str
    score: float
    chroma_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)

class RAGService:
    """Manages vector store + BM25 + cross-encoder for hybrid retrieval."""

    def __init__(self):
        self._embedder: Optional[SentenceTransformer] = None
        self._cross_encoder: Optional[CrossEncoder] = None
        self._chroma_client: Optional[chromadb.HttpClient] = None
        self._collection = None
        self._bm25: Optional[BM25Okapi] = None
        self._bm25_corpus: list[dict] = []

    def _get_embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            self._embedder = SentenceTransformer(settings.embedding_model)
        return self._embedder

    def _get_cross_encoder(self) -> CrossEncoder:
        if self._cross_encoder is None:
            logger.info("Loading cross-encoder: ms-marco-MiniLM-L-6-v2")
            self._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        return self._cross_encoder

    def _get_chroma(self):
        if self._chroma_client is None:
            try:
                self._chroma_client = chromadb.HttpClient(
                    host=settings.chromadb_host, port=settings.chromadb_port
                )
            except Exception:
                logger.warning("ChromaDB HTTP unavailable; using ephemeral client")
                self._chroma_client = chromadb.EphemeralClient()
        if self._collection is None:
            self._collection = self._chroma_client.get_or_create_collection(
                name="cyphermind_kb",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def rebuild_bm25(self, corpus: list[dict]):
        """Rebuild BM25 index from list of {content, source, ...} dicts."""
        self._bm25_corpus = corpus
        tokenized = [doc["content"].lower().split() for doc in corpus]
        self._bm25 = BM25Okapi(tokenized)
        logger.info(f"BM25 index built with {len(corpus)} documents")

    def add_chunk(self, chunk_id: str, content: str, metadata: dict):
        """Add single chunk to ChromaDB and BM25 corpus."""
        col = self._get_chroma()
        embedder = self._get_embedder()
        embedding = embedder.encode(content).tolist()
        col.add(ids=[chunk_id], documents=[content], embeddings=[embedding], metadatas=[metadata])

        self._bm25_corpus.append({"content": content, "source": metadata.get("source", ""), "id": chunk_id})
        tokenized = [doc["content"].lower().split() for doc in self._bm25_corpus]
        self._bm25 = BM25Okapi(tokenized)

    def _vector_search(self, query: str, k: int = 20) -> list[tuple[str, float]]:
        """Returns list of (doc_content, score)."""
        col = self._get_chroma()
        embedder = self._get_embedder()
        q_emb = embedder.encode(query).tolist()
        results = col.query(query_embeddings=[q_emb], n_results=min(k, col.count() or 1))
        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        return [(doc, 1 - dist) for doc, dist in zip(docs, distances)]

    def _bm25_search(self, query: str, k: int = 20) -> list[tuple[str, float]]:
        """Returns list of (doc_content, score)."""
        if self._bm25 is None or not self._bm25_corpus:
            return []
        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [(self._bm25_corpus[i]["content"], float(scores[i])) for i in top_idx]

    @staticmethod
    def _rrf_fusion(
        ranked_lists: list[list[tuple[str, float]]],
        k: int = RRF_K,
    ) -> list[tuple[str, float]]:
        """
        Reciprocal Rank Fusion.
        score(d) = Σ 1 / (k + rank(d))
        """
        scores: dict[str, float] = {}
        for ranked in ranked_lists:
            for rank, (doc, _) in enumerate(ranked, start=1):
                scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        """
        Full hybrid pipeline:
        1. Vector search
        2. BM25 search
        3. RRF fusion
        4. Cross-encoder re-ranking
        """
        vector_results = self._vector_search(query, k=20)
        bm25_results = self._bm25_search(query, k=20)
        fused = self._rrf_fusion([vector_results, bm25_results])

        # Cross-encoder re-ranking on top-20 fused
        candidates = [doc for doc, _ in fused[:20]]
        if candidates:
            ce = self._get_cross_encoder()
            pairs = [(query, doc) for doc in candidates]
            ce_scores = ce.predict(pairs)
            reranked = sorted(zip(candidates, ce_scores), key=lambda x: x[1], reverse=True)
            return [
                RetrievedChunk(content=doc, source="knowledge_base", score=float(score))
                for doc, score in reranked[:top_k]
            ]

        return [
            RetrievedChunk(content=doc, source="knowledge_base", score=score)
            for doc, score in fused[:top_k]
        ]

    async def query_with_llm(self, query: str, session_history: list[dict] | None = None) -> str:
        """RAG pipeline: retrieve context → generate answer via NVIDIA LLM."""
        from app.services.llm_service import chat_completion

        chunks = self.retrieve(query)
        context = "\n\n---\n\n".join(c.content for c in chunks)

        system_prompt = (
            "You are CypherMind, an expert penetration testing AI assistant. "
            "Use the provided context from the security knowledge base to answer accurately. "
            "Cite CWE/CVE IDs when relevant. Be concise and technical."
        )

        messages = [{"role": "system", "content": system_prompt}]
        if session_history:
            messages.extend(session_history[-6:])
        messages.append({
            "role": "user",
            "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{query}",
        })

        return await chat_completion(messages, temperature=0.7, max_tokens=4096, role="rag")

# Singleton
rag_service = RAGService()
