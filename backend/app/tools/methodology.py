"""Bug bounty methodology phases — Cybernote 2026 workflow."""
from __future__ import annotations

METHODOLOGY_PHASES: list[dict] = [
    {
        "id": 1,
        "name": "passive_subdomain_enum",
        "title": "Passive Subdomain Enumeration",
        "description": "No traffic to target. crt.sh, subfinder, assetfinder, amass, findomain, chaos.",
        "signal": "passive",
        "tools": ["passive_subdomain_enum", "certificate_transparency"],
    },
    {
        "id": 2,
        "name": "active_subdomain_enum",
        "title": "Active Subdomain Enumeration & Bruteforce",
        "description": "DNS bruteforce with puredns/dnsx, permutations, ffuf subdomain fuzz.",
        "signal": "active",
        "tools": ["subdomain_bruteforce", "subdomain_fuzz"],
    },
    {
        "id": 3,
        "name": "infrastructure_mapping",
        "title": "Infrastructure Mapping (ASN/CIDR/IPs)",
        "description": "ASN lookup, CIDR expansion, reverse DNS, TLD expansion.",
        "signal": "passive",
        "tools": ["asn_lookup", "reverse_dns"],
    },
    {
        "id": 4,
        "name": "waf_origin_discovery",
        "title": "WAF Bypass & Origin IP Discovery",
        "description": "Historical DNS, favicon hash, security trails via web search.",
        "signal": "passive",
        "tools": ["web_search", "http_probe"],
    },
    {
        "id": 5,
        "name": "alive_host_detection",
        "title": "Merge, Resolve & Alive Host Detection",
        "description": "Merge subdomains, httpx alive check, CMS fingerprint.",
        "signal": "active",
        "tools": ["merge_subdomains", "httpx_alive_check"],
    },
    {
        "id": 6,
        "name": "vhost_enumeration",
        "title": "Virtual Host Enumeration",
        "description": "Host header fuzzing on discovered IPs.",
        "signal": "active",
        "tools": ["vhost_fuzz"],
    },
    {
        "id": 7,
        "name": "url_endpoint_discovery",
        "title": "URL & Endpoint Discovery",
        "description": "waybackurls, gau, katana, gospider, paramspider, URL merge.",
        "signal": "mixed",
        "tools": ["wayback_urls", "crawl_urls", "categorize_urls"],
    },
    {
        "id": 8,
        "name": "js_analysis",
        "title": "JavaScript Analysis & Secret Extraction",
        "description": "Extract JS URLs, scan for API keys, tokens, internal endpoints.",
        "signal": "active",
        "tools": ["extract_js_urls", "js_secret_scan"],
    },
    {
        "id": 9,
        "name": "directory_discovery",
        "title": "Directory & Sensitive File Discovery",
        "description": "ffuf/dirsearch fuzzing, sensitive file patterns from wayback.",
        "signal": "active",
        "tools": ["directory_fuzz", "sensitive_file_scan"],
    },
    {
        "id": 10,
        "name": "github_intel",
        "title": "GitHub & Source Code Intelligence",
        "description": "GitHub dorks, leaked secrets, endpoints in repos.",
        "signal": "passive",
        "tools": ["github_recon"],
    },
    {
        "id": 11,
        "name": "port_scanning",
        "title": "Port Scanning & Service Fingerprinting",
        "description": "naabu/nmap port scan, service version detection.",
        "signal": "active",
        "tools": ["port_scan", "run_nmap"],
    },
    {
        "id": 12,
        "name": "vuln_scanning",
        "title": "Automated Vulnerability Scanning",
        "description": "nuclei CVE/misconfig templates, nuclei exposures.",
        "signal": "active",
        "tools": ["run_nuclei", "run_nuclei_exposures"],
    },
    {
        "id": 13,
        "name": "subdomain_takeover",
        "title": "Subdomain Takeover Detection",
        "description": "CNAME dangling checks, subzy, S3 bucket takeover candidates.",
        "signal": "passive",
        "tools": ["subdomain_takeover_check"],
    },
]

PHASE_BY_NAME = {p["name"]: p for p in METHODOLOGY_PHASES}
PHASE_BY_ID = {p["id"]: p for p in METHODOLOGY_PHASES}

DEFAULT_PIPELINE = [
    "passive_subdomain_enum",
    "alive_host_detection",
    "url_endpoint_discovery",
    "js_analysis",
    "vuln_scanning",
    "subdomain_takeover",
]

FULL_PIPELINE = [p["name"] for p in METHODOLOGY_PHASES]
