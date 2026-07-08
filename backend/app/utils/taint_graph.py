"""
Taint Analysis Graph
====================
Pseudocode:
  1. Scan source lines for known Source / Sink / Propagator / Sanitizer patterns
  2. Build directed NetworkX graph: Source -> Propagator* -> Sink
  3. Find shortest path from any Source to any Sink avoiding Sanitizers
  4. Return vulnerability paths with confidence scores

Complexity: O(V + E) build, O(V(V+E)) for all-pairs shortest path
"""
from __future__ import annotations
import re
import hashlib
from dataclasses import dataclass
from typing import NamedTuple, Optional
import networkx as nx
import logging

logger = logging.getLogger(__name__)

# ── Pattern dictionaries ──────────────────────────────────────────────────────
SOURCE_PATTERNS = [
    (r"request\.(GET|POST|args|form|data|json|files)\b", "HTTP_INPUT"),
    (r"sys\.argv\b", "CLI_ARG"),
    (r"os\.environ\b", "ENV_VAR"),
    (r"open\s*\(", "FILE_READ"),
    (r"input\s*\(", "USER_INPUT"),
]

SINK_PATTERNS = [
    (r"os\.(system|popen|execv?p?e?)\s*\(", "OS_EXEC"),
    (r"subprocess\.(call|run|Popen)\s*\(", "SUBPROCESS"),
    (r"eval\s*\(", "EVAL"),
    (r"exec\s*\(", "EXEC"),
    (r"cursor\.execute\s*\(", "SQL_EXEC"),
    (r"\.execute\s*\(", "DB_EXEC"),
    (r"render_template_string\s*\(", "TEMPLATE_INJECT"),
    (r"pickle\.loads\s*\(", "PICKLE_DESER"),
]

SANITIZER_PATTERNS = [
    (r"re\.(match|fullmatch|search)\s*\(", "REGEX_VALIDATE"),
    (r"html\.escape\s*\(", "HTML_ESCAPE"),
    (r"shlex\.quote\s*\(", "SHELL_QUOTE"),
    (r"parameterized|placeholder|\?|\%s", "PARAMETERIZED_QUERY"),
    (r"bleach\.clean\s*\(", "BLEACH_CLEAN"),
]

PROPAGATOR_PATTERNS = [
    (r"(\w+)\s*=\s*", "ASSIGNMENT"),
    (r"return\s+", "RETURN"),
    (r"\.format\s*\(", "STR_FORMAT"),
    (r"f['\"].*\{", "F_STRING"),
    (r"\+\s*\w+", "CONCAT"),
]

class TaintNode(NamedTuple):
    node_id: str
    node_type: str        # source | sink | propagator | sanitizer
    label: str
    file_path: str
    line_number: int
    code_snippet: str

@dataclass
class VulnerabilityPath:
    source: TaintNode
    sink: TaintNode
    path: list[TaintNode]
    has_sanitizer: bool
    confidence: float
    vuln_type: str

class TaintGraph:
    """In-memory taint analysis graph backed by NetworkX."""

    def __init__(self):
        self.graph: nx.DiGraph = nx.DiGraph()
        self._nodes: dict[str, TaintNode] = {}

    def _make_id(self, file_path: str, line: int, label: str) -> str:
        raw = f"{file_path}:{line}:{label}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def add_node(self, node: TaintNode):
        self._nodes[node.node_id] = node
        self.graph.add_node(
            node.node_id,
            node_type=node.node_type,
            label=node.label,
            file_path=node.file_path,
            line_number=node.line_number,
        )

    def add_edge(self, src_id: str, tgt_id: str, edge_type: str = "data_flow"):
        self.graph.add_edge(src_id, tgt_id, edge_type=edge_type)

    def analyze_file(self, file_path: str, source_code: str) -> list[TaintNode]:
        """Scan source code lines and add nodes to graph."""
        nodes_added = []
        lines = source_code.split("\n")

        last_propagator_id: Optional[str] = None

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            added = False
            for pattern, label in SANITIZER_PATTERNS:
                if re.search(pattern, stripped):
                    nid = self._make_id(file_path, lineno, label)
                    n = TaintNode(nid, "sanitizer", label, file_path, lineno, stripped[:120])
                    self.add_node(n)
                    if last_propagator_id:
                        self.add_edge(last_propagator_id, nid)
                    last_propagator_id = nid
                    nodes_added.append(n)
                    added = True
                    break

            if not added:
                for pattern, label in SOURCE_PATTERNS:
                    if re.search(pattern, stripped):
                        nid = self._make_id(file_path, lineno, label)
                        n = TaintNode(nid, "source", label, file_path, lineno, stripped[:120])
                        self.add_node(n)
                        last_propagator_id = nid
                        nodes_added.append(n)
                        added = True
                        break

            if not added:
                for pattern, label in SINK_PATTERNS:
                    if re.search(pattern, stripped):
                        nid = self._make_id(file_path, lineno, label)
                        n = TaintNode(nid, "sink", label, file_path, lineno, stripped[:120])
                        self.add_node(n)
                        if last_propagator_id:
                            self.add_edge(last_propagator_id, nid)
                        nodes_added.append(n)
                        added = True
                        break

            if not added:
                for pattern, label in PROPAGATOR_PATTERNS:
                    if re.search(pattern, stripped):
                        nid = self._make_id(file_path, lineno, label)
                        n = TaintNode(nid, "propagator", label, file_path, lineno, stripped[:120])
                        self.add_node(n)
                        if last_propagator_id:
                            self.add_edge(last_propagator_id, nid)
                        last_propagator_id = nid
                        nodes_added.append(n)
                        break

        return nodes_added

    def find_vulnerable_paths(self) -> list[VulnerabilityPath]:
        """
        Find Source→Sink paths. Paths through Sanitizers get lower confidence.

        Returns list of VulnerabilityPath sorted by confidence desc.
        """
        sources = [n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "source"]
        sinks   = [n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "sink"]
        sanitizers = {n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "sanitizer"}

        paths = []
        for src in sources:
            for snk in sinks:
                try:
                    for path_ids in nx.all_simple_paths(self.graph, src, snk, cutoff=20):
                        has_sanitizer = bool(sanitizers & set(path_ids))
                        path_nodes = [self._nodes[n] for n in path_ids if n in self._nodes]
                        src_node = self._nodes.get(src)
                        snk_node = self._nodes.get(snk)
                        if src_node and snk_node:
                            confidence = 0.3 if has_sanitizer else 0.85
                            vuln_type = f"{src_node.label}→{snk_node.label}"
                            paths.append(VulnerabilityPath(
                                source=src_node,
                                sink=snk_node,
                                path=path_nodes,
                                has_sanitizer=has_sanitizer,
                                confidence=confidence,
                                vuln_type=vuln_type,
                            ))
                except nx.NetworkXNoPath:
                    pass
                except nx.NodeNotFound:
                    pass

        return sorted(paths, key=lambda p: p.confidence, reverse=True)

    def to_dict(self) -> dict:
        """Serialize graph to JSON-safe dict for frontend visualization."""
        return {
            "nodes": [
                {
                    "id": nid,
                    "type": d.get("node_type"),
                    "label": d.get("label"),
                    "file": d.get("file_path"),
                    "line": d.get("line_number"),
                }
                for nid, d in self.graph.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, "type": d.get("edge_type", "data_flow")}
                for u, v, d in self.graph.edges(data=True)
            ],
        }
