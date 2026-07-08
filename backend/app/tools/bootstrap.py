"""Register all pentest tools on the global registry."""
import app.tools.methodology_tools  # noqa: F401 — methodology recon tools
from app.tools.registry import tool_registry
from app.tools import security_tools
from app.tools.web_search import google_search


@tool_registry.register(
    "web_search",
    "Search the web for CVEs, exploit writeups, bug bounty tips, technology fingerprints, or security advisories.",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {"type": "integer", "description": "Number of results (1-10)", "default": 5},
        },
        "required": ["query"],
    },
    category="recon",
)
async def _web_search(query: str, num_results: int = 5, _context=None):
    results = await google_search(query, num_results)
    return {"query": query, "results": results, "count": len(results)}


@tool_registry.register(
    "http_probe",
    "HTTP GET/HEAD a URL. Returns status, headers, security header analysis, body preview.",
    {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "method": {"type": "string", "enum": ["GET", "HEAD", "POST"], "default": "GET"},
        },
        "required": ["url"],
    },
    category="recon",
)
async def _http_probe(url: str, method: str = "GET", _context=None):
    ctx = _context or {}
    scope = ctx.get("scope_domains", [])
    if scope:
        check = security_tools.check_scope(url, scope)
        if not check.get("in_scope"):
            return {"error": "OUT OF SCOPE", **check}
    return await security_tools.http_probe(url, method)


@tool_registry.register(
    "dns_resolve",
    "Resolve hostname to IP addresses.",
    {"type": "object", "properties": {"hostname": {"type": "string"}}, "required": ["hostname"]},
    category="recon",
)
async def _dns_resolve(hostname: str, _context=None):
    return await security_tools.dns_resolve(hostname)


@tool_registry.register(
    "check_scope",
    "Check if a URL/host is within the bug bounty program scope.",
    {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
    category="scope",
)
async def _check_scope(url: str, _context=None):
    scope = (_context or {}).get("scope_domains", [])
    return security_tools.check_scope(url, scope)


@tool_registry.register(
    "generate_payloads",
    "Generate bug bounty test payloads for sqli, xss, ssrf, lfi, open_redirect, idor.",
    {
        "type": "object",
        "properties": {
            "vuln_type": {
                "type": "string",
                "enum": ["sqli", "xss", "ssrf", "lfi", "open_redirect", "idor"],
            },
            "target_param": {"type": "string", "description": "Optional parameter name prefix"},
        },
        "required": ["vuln_type"],
    },
    category="exploit",
)
async def _generate_payloads(vuln_type: str, target_param: str = "", _context=None):
    return security_tools.generate_payloads(vuln_type, target_param)


@tool_registry.register(
    "run_nuclei",
    "Run ProjectDiscovery Nuclei vulnerability scanner against a URL (must be in scope).",
    {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "severity": {"type": "string", "default": "critical,high,medium"},
        },
        "required": ["url"],
    },
    category="scan",
)
async def _run_nuclei(url: str, severity: str = "critical,high,medium", _context=None):
    ctx = _context or {}
    scope = ctx.get("scope_domains", [])
    if scope:
        check = security_tools.check_scope(url, scope)
        if not check.get("in_scope"):
            return {"error": "OUT OF SCOPE", **check}
    return await security_tools.run_nuclei(url, severity)


@tool_registry.register(
    "run_nmap",
    "Port scan a host with nmap service detection.",
    {
        "type": "object",
        "properties": {
            "host": {"type": "string"},
            "ports": {"type": "string", "default": "80,443,8080,8443"},
        },
        "required": ["host"],
    },
    category="scan",
)
async def _run_nmap(host: str, ports: str = "80,443,8080,8443", _context=None):
    return await security_tools.run_nmap(host, ports)


@tool_registry.register(
    "cve_lookup",
    "Look up CVE details from NVD (description, CVSS, CWE).",
    {
        "type": "object",
        "properties": {"cve_id": {"type": "string", "description": "e.g. CVE-2024-1234"}},
        "required": ["cve_id"],
    },
    category="intel",
)
async def _cve_lookup(cve_id: str, _context=None):
    return await security_tools.cve_lookup(cve_id)


@tool_registry.register(
    "search_knowledge_base",
    "Search the local security knowledge base (RAG) for techniques, code patterns, writeups.",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
    category="intel",
)
async def _search_kb(query: str, top_k: int = 5, _context=None):
    return await security_tools.knowledge_search(query, top_k)


@tool_registry.register(
    "search_exploits",
    "Search public exploit databases and GitHub for exploit PoCs related to a query/CVE.",
    {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    category="intel",
)
async def _search_exploits(query: str, _context=None):
    return await security_tools.search_exploit_db(query)


@tool_registry.register(
    "report_finding",
    "Report a confirmed or suspected vulnerability finding. Use when you discover a bug.",
    {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "severity": {"type": "string", "enum": ["critical", "high", "medium", "low", "info"]},
            "description": {"type": "string"},
            "cwe_id": {"type": "string"},
            "cve_id": {"type": "string"},
            "payload": {"type": "string"},
            "url": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["title", "severity", "description"],
    },
    category="reporting",
)
async def _report_finding(
    title: str,
    severity: str,
    description: str,
    cwe_id: str = "",
    cve_id: str = "",
    payload: str = "",
    url: str = "",
    confidence: float = 0.7,
    _context=None,
):
    finding = {
        "title": title,
        "severity": severity.lower(),
        "description": description,
        "cwe_id": cwe_id or None,
        "cve_id": cve_id or None,
        "payload": payload or None,
        "confidence": confidence,
        "is_novel": True,
        "is_verified": confidence >= 0.8,
    }
    ctx = _context or {}
    if ctx.get("findings_collector") is not None:
        ctx["findings_collector"].append(finding)
    return {"recorded": True, "finding": finding}
