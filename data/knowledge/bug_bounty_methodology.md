# Bug Bounty Methodology Reference (Cybernote 2026)

## Phase 1 — Passive Subdomain Enumeration
Passive sources: crt.sh, subfinder, assetfinder, amass, findomain, chaos, github-subdomains.
No direct traffic to target.

## Phase 2 — Active Subdomain Bruteforce
DNS bruteforce with puredns/dnsx, gotator permutations, ffuf subdomain fuzz.

## Phase 3 — Infrastructure Mapping
ASN lookup, CIDR expansion, reverse DNS PTR, TLD expansion.

## Phase 4 — WAF / Origin IP Discovery
Favicon hash + Shodan, historical DNS, Google Analytics ID relationships.

## Phase 5 — Alive Host Detection
Merge subdomains, httpx probe, gowitness screenshots, whatweb CMS fingerprint.

## Phase 6 — Virtual Host Enumeration
Host header fuzzing on IPs: `Host: FUZZ.target.com`

## Phase 7 — URL & Endpoint Discovery
waybackurls, gau, katana, gospider, paramspider. Categorize: JS, API, auth, admin, IDOR, redirect.

## Phase 8 — JavaScript Analysis
Extract JS URLs, scan for API keys, tokens, AWS keys, private keys, source maps.

## Phase 9 — Directory & Sensitive Files
ffuf/dirsearch fuzzing, wayback sensitive file patterns (.env, .bak, .sql).

## Phase 10 — GitHub Intelligence
GitDorker, trufflehog, git-wild-hunt, GitLab token abuse.

## Phase 11 — Port Scanning
naabu top ports, nmap -sV -sC service detection.

## Phase 12 — Automated Vuln Scanning
nuclei CVE/exposure templates, sqlmap on parameterized URLs.

## Phase 13 — Subdomain Takeover
subzy, CNAME dangling to Heroku/S3/Zendesk/GitHub Pages.

## High-Value Bug Classes
- SQLi, SSRF, IDOR, auth bypass, stored XSS, RCE, subdomain takeover, exposed secrets
- Use enrich_finding_with_rag for CVE/CWE context before reporting

## CWE References
- CWE-89 SQL Injection
- CWE-79 XSS
- CWE-918 SSRF
- CWE-639 IDOR
- CWE-287 Authentication Bypass
- CWE-200 Information Exposure
