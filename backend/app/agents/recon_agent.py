"""
ReconAgent — The Scout
=======================
Tools: nmap, subfinder (optional), httpx (optional)
Output: open ports, service banners, tech stack, subdomains
"""
from __future__ import annotations
import asyncio
import json
import shutil
import subprocess
import logging
from .base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

class ReconAgent(BaseAgent):
    name = "ReconAgent"
    description = "Network reconnaissance: port scanning, service detection, subdomain enumeration"

    async def run(self, target: dict, context: dict) -> AgentResult:
        findings = []
        outputs = {}

        ip_or_url = target.get("ip_address") or target.get("url", "127.0.0.1")
        host = ip_or_url.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]

        # ── Nmap scan ────────────────────────────────────────────────────────
        if shutil.which("nmap"):
            nmap_result = await self._nmap_scan(host)
            outputs["nmap"] = nmap_result
            findings.extend(self._parse_nmap(nmap_result, host))
        else:
            logger.warning("nmap not found; skipping port scan")
            outputs["nmap"] = "nmap not installed"

        # ── Subfinder ────────────────────────────────────────────────────────
        if shutil.which("subfinder"):
            sub_result = await self._subfinder(host)
            outputs["subfinder"] = sub_result
        else:
            outputs["subfinder"] = "subfinder not installed"

        return AgentResult(
            agent_name=self.name,
            status="success",
            findings=findings,
            tool_outputs=outputs,
        )

    async def _nmap_scan(self, host: str) -> str:
        """Run nmap service/version detection."""
        cmd = ["nmap", "-sV", "--script=banner", "-T4", "-p", "22,80,443,8080,8443,3306,5432,6379,27017", host]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            return stdout.decode(errors="replace")
        except asyncio.TimeoutError:
            return "nmap scan timed out"
        except Exception as e:
            return f"nmap error: {e}"

    def _parse_nmap(self, nmap_output: str, host: str) -> list[dict]:
        """Extract open ports from nmap output and create findings."""
        findings = []
        for line in nmap_output.splitlines():
            if "/tcp" in line and "open" in line:
                parts = line.split()
                port = parts[0].split("/")[0]
                service = parts[2] if len(parts) > 2 else "unknown"
                version = " ".join(parts[3:]) if len(parts) > 3 else ""
                severity = "info"
                if service in ("ftp", "telnet"):
                    severity = "high"
                elif service in ("mysql", "postgresql", "redis", "mongodb"):
                    severity = "medium"
                findings.append(self._make_finding(
                    title=f"Open port {port}/{service} on {host}",
                    severity=severity,
                    description=f"Service: {service} {version}",
                    confidence=0.95,
                ))
        return findings

    async def _subfinder(self, domain: str) -> str:
        cmd = ["subfinder", "-d", domain, "-silent"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
            return stdout.decode(errors="replace")
        except Exception as e:
            return f"subfinder error: {e}"
