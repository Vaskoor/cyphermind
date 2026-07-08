"""
SASTAgent — The Bug Finder
===========================
Tools: Semgrep, Bandit, TruffleHog
Advanced: Taint Analysis via TaintGraph
Output: vulnerability list with CWE, confidence, data-flow paths
"""
from __future__ import annotations
import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from .base import BaseAgent, AgentResult
from app.utils.taint_graph import TaintGraph
from app.utils.ast_chunker import chunk_file
import logging

logger = logging.getLogger(__name__)

class SASTAgent(BaseAgent):
    name = "SASTAgent"
    description = "Static analysis: Semgrep, Bandit, secrets detection, taint analysis"

    async def run(self, target: dict, context: dict) -> AgentResult:
        findings = []
        outputs = {}
        code_path = target.get("code_path")

        if not code_path or not Path(code_path).exists():
            return AgentResult(
                agent_name=self.name,
                status="failed",
                error="code_path not provided or does not exist",
            )

        # ── Semgrep ───────────────────────────────────────────────────────────
        if shutil.which("semgrep"):
            sg_result = await self._run_semgrep(code_path)
            outputs["semgrep"] = sg_result
            findings.extend(self._parse_semgrep(sg_result))
        else:
            outputs["semgrep"] = "semgrep not installed"

        # ── Bandit ────────────────────────────────────────────────────────────
        if shutil.which("bandit"):
            bandit_result = await self._run_bandit(code_path)
            outputs["bandit"] = bandit_result
            findings.extend(self._parse_bandit(bandit_result))
        else:
            outputs["bandit"] = "bandit not installed"

        # ── TruffleHog / secrets ──────────────────────────────────────────────
        if shutil.which("trufflehog"):
            th_result = await self._run_trufflehog(code_path)
            outputs["trufflehog"] = th_result
        else:
            outputs["trufflehog"] = "trufflehog not installed"

        # ── Taint analysis ────────────────────────────────────────────────────
        taint_graph = TaintGraph()
        for py_file in Path(code_path).rglob("*.py"):
            source = py_file.read_text(encoding="utf-8", errors="replace")
            taint_graph.analyze_file(str(py_file), source)

        vuln_paths = taint_graph.find_vulnerable_paths()
        for vp in vuln_paths[:20]:  # cap at 20
            if not vp.has_sanitizer:
                findings.append(self._make_finding(
                    title=f"Taint Flow: {vp.vuln_type}",
                    severity="high" if vp.confidence > 0.7 else "medium",
                    description=f"Unsanitized taint path from {vp.source.label} to {vp.sink.label}",
                    cwe_id="CWE-20",
                    file_path=vp.source.file_path,
                    line_number=vp.source.line_number,
                    confidence=vp.confidence,
                ))

        outputs["taint_graph"] = taint_graph.to_dict()

        return AgentResult(
            agent_name=self.name,
            status="success",
            findings=findings,
            tool_outputs=outputs,
        )

    async def _run_semgrep(self, path: str) -> dict:
        cmd = ["semgrep", "--config=auto", "--json", path]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
            return json.loads(stdout.decode(errors="replace") or "{}")
        except Exception as e:
            return {"error": str(e)}

    def _parse_semgrep(self, result: dict) -> list[dict]:
        findings = []
        for r in result.get("results", []):
            sev_map = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}
            sev = sev_map.get(r.get("extra", {}).get("severity", "INFO"), "low")
            meta = r.get("extra", {}).get("metadata", {})
            findings.append(self._make_finding(
                title=r.get("check_id", "semgrep-finding"),
                severity=sev,
                description=r.get("extra", {}).get("message", ""),
                cwe_id=meta.get("cwe", [None])[0] if isinstance(meta.get("cwe"), list) else meta.get("cwe"),
                file_path=r.get("path"),
                line_number=r.get("start", {}).get("line"),
                confidence=0.8,
            ))
        return findings

    async def _run_bandit(self, path: str) -> dict:
        cmd = ["bandit", "-r", path, "-f", "json", "-q"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
            return json.loads(stdout.decode(errors="replace") or "{}")
        except Exception as e:
            return {"error": str(e)}

    def _parse_bandit(self, result: dict) -> list[dict]:
        sev_map = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
        findings = []
        for r in result.get("results", []):
            findings.append(self._make_finding(
                title=r.get("test_name", "bandit-finding"),
                severity=sev_map.get(r.get("issue_severity", "LOW"), "low"),
                description=r.get("issue_text", ""),
                cwe_id=r.get("issue_cwe", {}).get("id"),
                file_path=r.get("filename"),
                line_number=r.get("line_number"),
                confidence=0.75,
            ))
        return findings

    async def _run_trufflehog(self, path: str) -> str:
        cmd = ["trufflehog", "filesystem", path, "--json"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
            return stdout.decode(errors="replace")
        except Exception as e:
            return f"trufflehog error: {e}"
