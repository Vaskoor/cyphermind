"""Register bug bounty methodology / recon tools."""
from app.tools.registry import tool_registry
from app.tools import recon_tools
from app.tools.methodology import DEFAULT_PIPELINE, FULL_PIPELINE
from app.tools.wordlists import wordlist_status


@tool_registry.register(
    "passive_subdomain_enum",
    "Phase 1: Passive subdomain enumeration via crt.sh, subfinder, assetfinder, findomain, chaos.",
    {
        "type": "object",
        "properties": {"domain": {"type": "string", "description": "Root domain e.g. target.com"}},
        "required": ["domain"],
    },
    category="recon",
)
async def _passive_subdomain_enum(domain: str, _context=None):
    return await recon_tools.passive_subdomain_enum(domain, _context)


@tool_registry.register(
    "certificate_transparency",
    "Query crt.sh certificate transparency logs for subdomains.",
    {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]},
    category="recon",
)
async def _certificate_transparency(domain: str, _context=None):
    return await recon_tools.certificate_transparency(domain)


@tool_registry.register(
    "subdomain_bruteforce",
    "Phase 2: Active DNS bruteforce using dnsx/puredns and DNS wordlist.",
    {
        "type": "object",
        "properties": {
            "domain": {"type": "string"},
            "limit": {"type": "integer", "default": 500},
        },
        "required": ["domain"],
    },
    category="recon",
)
async def _subdomain_bruteforce(domain: str, limit: int = 500, _context=None):
    return await recon_tools.subdomain_bruteforce(domain, limit, _context)


@tool_registry.register(
    "subdomain_fuzz",
    "FFuf subdomain fuzzing (FUZZ.target.com patterns).",
    {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]},
    category="recon",
)
async def _subdomain_fuzz(domain: str, _context=None):
    return await recon_tools.subdomain_fuzz(domain, _context)


@tool_registry.register(
    "asn_lookup",
    "Phase 3: ASN and infrastructure lookup for a domain.",
    {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]},
    category="recon",
)
async def _asn_lookup(domain: str, _context=None):
    return await recon_tools.asn_lookup(domain)


@tool_registry.register(
    "reverse_dns",
    "Reverse DNS (PTR) lookup on IP or CIDR.",
    {"type": "object", "properties": {"ip_or_cidr": {"type": "string"}}, "required": ["ip_or_cidr"]},
    category="recon",
)
async def _reverse_dns(ip_or_cidr: str, _context=None):
    return await recon_tools.reverse_dns(ip_or_cidr)


@tool_registry.register(
    "merge_subdomains",
    "Merge all discovered subdomains from recon state.",
    {"type": "object", "properties": {}},
    category="recon",
)
async def _merge_subdomains(_context=None):
    return await recon_tools.merge_subdomains(_context)


@tool_registry.register(
    "httpx_alive_check",
    "Phase 5: Probe subdomains for alive HTTP/HTTPS hosts with httpx.",
    {
        "type": "object",
        "properties": {"hosts": {"type": "array", "items": {"type": "string"}}},
    },
    category="recon",
)
async def _httpx_alive_check(hosts: list[str] | None = None, _context=None):
    return await recon_tools.httpx_alive_check(hosts, _context)


@tool_registry.register(
    "vhost_fuzz",
    "Phase 6: Virtual host enumeration via Host header fuzzing on an IP.",
    {
        "type": "object",
        "properties": {
            "ip": {"type": "string"},
            "domain": {"type": "string"},
            "limit": {"type": "integer", "default": 100},
        },
        "required": ["ip", "domain"],
    },
    category="recon",
)
async def _vhost_fuzz(ip: str, domain: str, limit: int = 100, _context=None):
    return await recon_tools.vhost_fuzz(ip, domain, limit, _context)


@tool_registry.register(
    "wayback_urls",
    "Phase 7: Collect historical URLs from Wayback/gau/CDX API.",
    {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]},
    category="recon",
)
async def _wayback_urls(domain: str, _context=None):
    return await recon_tools.wayback_urls(domain, _context)


@tool_registry.register(
    "crawl_urls",
    "Active crawl with katana/gospider or basic link extraction.",
    {
        "type": "object",
        "properties": {"seed_url": {"type": "string"}},
        "required": ["seed_url"],
    },
    category="recon",
)
async def _crawl_urls(seed_url: str, _context=None):
    return await recon_tools.crawl_urls(seed_url, _context)


@tool_registry.register(
    "categorize_urls",
    "Categorize discovered URLs: JS, API, auth, admin, IDOR, redirect, sensitive.",
    {"type": "object", "properties": {}},
    category="recon",
)
async def _categorize_urls(_context=None):
    return recon_tools.categorize_urls(ctx=_context)


@tool_registry.register(
    "extract_js_urls",
    "Phase 8: Extract JavaScript file URLs from recon state.",
    {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]},
    category="recon",
)
async def _extract_js_urls(domain: str, _context=None):
    return await recon_tools.extract_js_urls(domain, _context)


@tool_registry.register(
    "js_secret_scan",
    "Scan JS files for API keys, tokens, AWS keys, private keys.",
    {"type": "object", "properties": {"js_urls": {"type": "array", "items": {"type": "string"}}}},
    category="recon",
)
async def _js_secret_scan(js_urls: list[str] | None = None, _context=None):
    return await recon_tools.js_secret_scan(js_urls, _context)


@tool_registry.register(
    "directory_fuzz",
    "Phase 9: Directory and file fuzzing with ffuf or Python fallback.",
    {
        "type": "object",
        "properties": {
            "base_url": {"type": "string"},
            "limit": {"type": "integer", "default": 200},
        },
        "required": ["base_url"],
    },
    category="recon",
)
async def _directory_fuzz(base_url: str, limit: int = 200, _context=None):
    return await recon_tools.directory_fuzz(base_url, limit, _context)


@tool_registry.register(
    "sensitive_file_scan",
    "Find sensitive file URLs (.env, .bak, .sql, etc.) from wayback/crawl data.",
    {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]},
    category="recon",
)
async def _sensitive_file_scan(domain: str, _context=None):
    return await recon_tools.sensitive_file_scan(domain, _context)


@tool_registry.register(
    "github_recon",
    "Phase 10: GitHub code search for leaked secrets and endpoints.",
    {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]},
    category="intel",
)
async def _github_recon(domain: str, _context=None):
    return await recon_tools.github_recon(domain)


@tool_registry.register(
    "port_scan",
    "Phase 11: Port scan with naabu or nmap.",
    {"type": "object", "properties": {"hosts": {"type": "array", "items": {"type": "string"}}}},
    category="scan",
)
async def _port_scan(hosts: list[str] | None = None, _context=None):
    return await recon_tools.port_scan(hosts, _context)


@tool_registry.register(
    "run_nuclei_exposures",
    "Phase 12: Nuclei exposure templates scan on a URL.",
    {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    category="scan",
)
async def _run_nuclei_exposures(url: str, _context=None):
    return await recon_tools.run_nuclei_exposures(url)


@tool_registry.register(
    "subdomain_takeover_check",
    "Phase 13: Subdomain takeover detection via subzy or CNAME heuristics.",
    {"type": "object", "properties": {"subdomains": {"type": "array", "items": {"type": "string"}}}},
    category="recon",
)
async def _subdomain_takeover_check(subdomains: list[str] | None = None, _context=None):
    return await recon_tools.subdomain_takeover_check(subdomains, _context)


@tool_registry.register(
    "run_methodology_pipeline",
    "Run automated bug bounty methodology pipeline (phases 1-13). Returns full recon briefing.",
    {
        "type": "object",
        "properties": {
            "domain": {"type": "string"},
            "phases": {
                "type": "array",
                "items": {"type": "string"},
                "description": f"Phase names. Default: {DEFAULT_PIPELINE}. Use 'full' for all 13 phases.",
            },
            "pipeline_mode": {"type": "string", "enum": ["default", "full", "custom"], "default": "default"},
        },
        "required": ["domain"],
    },
    category="recon",
)
async def _run_methodology_pipeline(
    domain: str,
    phases: list[str] | None = None,
    pipeline_mode: str = "default",
    _context=None,
):
    if pipeline_mode == "full":
        phases = FULL_PIPELINE
    elif pipeline_mode == "default" and not phases:
        phases = DEFAULT_PIPELINE
    return await recon_tools.run_methodology_pipeline(domain, phases, _context)


@tool_registry.register(
    "enrich_finding_with_rag",
    "Enrich a vulnerability finding with RAG knowledge base + web search for CVEs and exploitation.",
    {
        "type": "object",
        "properties": {
            "vuln_type": {"type": "string", "description": "e.g. SQL injection, XSS, SSRF"},
            "technology": {"type": "string", "description": "Optional tech stack hint"},
        },
        "required": ["vuln_type"],
    },
    category="intel",
)
async def _enrich_finding_with_rag(vuln_type: str, technology: str = "", _context=None):
    return await recon_tools.enrich_with_rag(vuln_type, technology)


@tool_registry.register(
    "search_attack_memory",
    "Search learned attack patterns from past hunts and self-play. Returns proven payloads and techniques.",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Vuln type, tech, or attack description"},
            "target_type": {"type": "string", "default": "web"},
        },
        "required": ["query"],
    },
    category="intel",
)
async def _search_attack_memory(query: str, target_type: str = "web", _context=None):
    from app.services.attack_memory_service import retrieve_attack_context
    from app.services.rag_service import rag_service

    ctx = _context or {}
    domain = ctx.get("target_domain") or ""
    tech = ctx.get("tech_stack") if isinstance(ctx.get("tech_stack"), list) else []
    result = await retrieve_attack_context(target_type, tech, domain)
    rag = rag_service.retrieve(f"{query} attack payload exploit", top_k=5)
    return {
        "query": query,
        "attack_intelligence": result.get("prompt_block", ""),
        "memory_count": len(result.get("db_memories") or []),
        "rag_matches": [{"content": c.content[:300], "score": c.score} for c in rag],
    }


@tool_registry.register(
    "wordlist_status",
    "Check configured DNS/web/params wordlist paths and line counts.",
    {"type": "object", "properties": {}},
    category="recon",
)
async def _wordlist_status(_context=None):
    return wordlist_status()
