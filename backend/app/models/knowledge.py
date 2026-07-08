"""Knowledge base: KnowledgeChunk, GraphNode, GraphEdge."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class KnowledgeChunk(Base):
    """RAG document chunk with metadata."""
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    chroma_id: Mapped[Optional[str]] = mapped_column(String(256), unique=True)
    content: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(64))    # cve, cwe, code, exploit, writeup
    source_path: Mapped[Optional[str]] = mapped_column(String(1024))
    language: Mapped[Optional[str]] = mapped_column(String(32))
    function_name: Mapped[Optional[str]] = mapped_column(String(256))
    line_start: Mapped[Optional[int]] = mapped_column(Integer)
    line_end: Mapped[Optional[int]] = mapped_column(Integer)
    cve_id: Mapped[Optional[str]] = mapped_column(String(64))
    cwe_id: Mapped[Optional[str]] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_json: Mapped[Optional[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class GraphNode(Base):
    """Taint analysis graph node: Source, Sink, Propagator, Sanitizer."""
    __tablename__ = "graph_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    node_type: Mapped[str] = mapped_column(String(32))   # source, sink, propagator, sanitizer
    label: Mapped[str] = mapped_column(String(256))
    file_path: Mapped[Optional[str]] = mapped_column(String(1024))
    line_number: Mapped[Optional[int]] = mapped_column(Integer)
    code_snippet: Mapped[Optional[str]] = mapped_column(Text)
    engagement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("engagements.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    outgoing: Mapped[list["GraphEdge"]] = relationship(
        "GraphEdge", foreign_keys="GraphEdge.source_node_id", back_populates="source"
    )
    incoming: Mapped[list["GraphEdge"]] = relationship(
        "GraphEdge", foreign_keys="GraphEdge.target_node_id", back_populates="target"
    )

class GraphEdge(Base):
    """Directed edge in taint analysis graph."""
    __tablename__ = "graph_edges"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_node_id: Mapped[str] = mapped_column(ForeignKey("graph_nodes.node_id"))
    target_node_id: Mapped[str] = mapped_column(ForeignKey("graph_nodes.node_id"))
    edge_type: Mapped[str] = mapped_column(String(64))    # data_flow, call, assignment
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    source: Mapped["GraphNode"] = relationship(
        "GraphNode", foreign_keys=[source_node_id], back_populates="outgoing"
    )
    target: Mapped["GraphNode"] = relationship(
        "GraphNode", foreign_keys=[target_node_id], back_populates="incoming"
    )
