"""Unit tests for taint analysis."""
from app.utils.taint_graph import TaintGraph

VULNERABLE_CODE = """
import os
from flask import request

def exec_cmd():
    cmd = request.GET.get('cmd')
    os.system(cmd)
"""


def test_taint_graph_finds_sources_and_sinks():
    g = TaintGraph()
    nodes = g.analyze_file("test.py", VULNERABLE_CODE)
    types = [n.node_type for n in nodes]
    assert "source" in types
    assert "sink" in types


def test_taint_graph_finds_vulnerable_path():
    g = TaintGraph()
    g.analyze_file("test.py", VULNERABLE_CODE)
    paths = g.find_vulnerable_paths()
    assert len(paths) > 0
