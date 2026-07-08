"""
AST-Based Code Chunker
======================
Pseudocode:
  1. Parse source file with tree-sitter
  2. Walk AST, find function_definition nodes
  3. Extract node text + metadata
  4. Yield chunks with function-level granularity

Complexity: O(n) where n = number of nodes in AST
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class CodeChunk:
    """Single function-level code chunk for RAG ingestion."""
    content: str
    language: str
    file_path: str
    function_name: str
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    metadata: dict = field(default_factory=dict)

def _extract_docstring(source: str) -> Optional[str]:
    """Extract leading docstring from a function body (simple heuristic)."""
    lines = source.strip().split("\n")
    in_triple = False
    doc_lines = []
    for line in lines[1:]:  # skip def line
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if in_triple:
                doc_lines.append(stripped)
                return "\n".join(doc_lines)
            in_triple = True
        if in_triple:
            doc_lines.append(stripped)
    return None

def chunk_python_file(file_path: str) -> Iterator[CodeChunk]:
    """
    Parse a Python file using tree-sitter and yield CodeChunk per function.

    Falls back to regex-based splitting if tree-sitter is unavailable.
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"File not found: {file_path}")
        return

    source = path.read_text(encoding="utf-8", errors="replace")

    try:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser

        PY_LANGUAGE = Language(tspython.language())
        parser = Parser(PY_LANGUAGE)
        tree = parser.parse(bytes(source, "utf-8"))

        def walk(node):
            if node.type == "function_definition":
                fn_bytes = source.encode("utf-8")[node.start_byte:node.end_byte]
                fn_text = fn_bytes.decode("utf-8", errors="replace")
                name_node = next(
                    (c for c in node.children if c.type == "identifier"), None
                )
                fn_name = name_node.text.decode() if name_node else "unknown"
                yield CodeChunk(
                    content=fn_text,
                    language="python",
                    file_path=file_path,
                    function_name=fn_name,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    docstring=_extract_docstring(fn_text),
                )
            for child in node.children:
                yield from walk(child)

        yield from walk(tree.root_node)

    except ImportError:
        logger.warning("tree-sitter not available; falling back to regex chunker")
        yield from _regex_chunk_python(source, file_path)

def _regex_chunk_python(source: str, file_path: str) -> Iterator[CodeChunk]:
    """Fallback regex-based function extractor."""
    import re
    pattern = re.compile(r'^(def\s+(\w+)\s*\(.*?\):.*?)(?=\ndef\s|\Z)', re.MULTILINE | re.DOTALL)
    for match in pattern.finditer(source):
        fn_text = match.group(1)
        fn_name = match.group(2)
        start_line = source[:match.start()].count("\n") + 1
        end_line = start_line + fn_text.count("\n")
        yield CodeChunk(
            content=fn_text,
            language="python",
            file_path=file_path,
            function_name=fn_name,
            line_start=start_line,
            line_end=end_line,
        )

def chunk_file(file_path: str) -> Iterator[CodeChunk]:
    """Dispatch chunker based on file extension."""
    ext = Path(file_path).suffix.lower()
    if ext == ".py":
        yield from chunk_python_file(file_path)
    else:
        # Generic: whole file as single chunk
        source = Path(file_path).read_text(encoding="utf-8", errors="replace")
        yield CodeChunk(
            content=source,
            language=ext.lstrip(".") or "text",
            file_path=file_path,
            function_name="__file__",
            line_start=1,
            line_end=source.count("\n") + 1,
        )
