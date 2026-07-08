"""Full bug bounty recon toolkit — methodology phases 1-13."""
from __future__ import annotations

import asyncio
import json
import re
import shutil
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import get_settings
from app.tools.wordlists import resolve_wordlist, WORDLIST_DIR

settings = get_settings()

# Shared recon state keyed by engagement/job id in context
RECON_STATE: dict[str, dict] = {}


def _domain_from_target(domain: str) -> str:
    domain = domain.strip().lower()
    if "://" in domain:
        domain = urlparse(domain).hostname or domain
    return domain.split(":")[0]


def _state_key(ctx: dict | None) -> str:
    if not ctx:
        return "default"
    return str(ctx.get("job_id") or ctx.get("target_url") or ctx.get("engagement_id") or "default")


def _get_state(ctx: dict | None) -> dict:
    key = _state_key(ctx)
    if key not in RECON_STATE:
        RECON_STATE[key] = {
            "subdomains": set(),
            "alive_hosts": set(),
            "urls": set(),
            "js_urls": set(),
            "ips": set(),
        }
    return RECON_STATE[key]


async def _run_cmd(cmd: list[str], timeout: int = 120) -> tuple[str, str, int]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode(errors="replace"), stderr.decode(errors="replace"), proc.returncode or 0
    except asyncio.TimeoutError:
        return "", "timeout", -1
    except FileNotFoundError:
        return "", "command not found", -1


# ── Phase 1: Passive subdomain enum ──────────────────────────────────────────

async def certificate_transparency(domain: str) -> dict:
    domain = _domain_from_target(domain)
    subs: set[str] = set()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://crt.sh/?q=%25.{domain}&output=json",
            )
            if resp.status_code == 200:
                data = resp.json()
                for entry in data:
                    nv = entry.get("name_value", "")
                    for part in nv.split("\n"):
                        part = part.strip().lower().replace("*.", "")
                        if part.endswith(domain) and " " not in part:
                            subs.add(part)
    except Exception as exc:
        return {"domain": domain, "error": str(exc), "count": 0, "subdomains": []}

    return {"domain": domain, "count": len(subs), "subdomains": sorted(subs)[:500]}


async def passive_subdomain_enum(domain: str, ctx: dict | None = None) -> dict:
    domain = _domain_from_target(domain)
    state = _get_state(ctx)
    all_subs: set[str] = set()

    # crt.sh
    crt_result = await certificate_transparency(domain)
    all_subs.update(crt_result.get("subdomains", []))

    # subfinder
    if shutil.which("subfinder"):
        out, _, code = await _run_cmd(
            ["subfinder", "-d", domain, "-all", "-silent"], timeout=180
        )
        if code == 0:
            all_subs.update(line.strip() for line in out.splitlines() if line.strip())

    # assetfinder
    if shutil.which("assetfinder"):
        out, _, _ = await _run_cmd(["assetfinder", "--subs-only", domain])
        all_subs.update(line.strip() for line in out.splitlines() if line.strip())

    # chaos (ProjectDiscovery)
    if shutil.which("chaos") and settings.pdcp_api_key:
        out, _, _ = await _run_cmd(
            ["chaos", "-d", domain, "-silent", "-key", settings.pdcp_api_key]
        )
        all_subs.update(line.strip() for line in out.splitlines() if line.strip())

    # findomain
    if shutil.which("findomain"):
        tmp = WORDLIST_DIR / f"_findomain_{domain}.txt"
        await _run_cmd(["findomain", "-t", domain, "-u", str(tmp)])
        if tmp.exists():
            all_subs.update(line.strip() for line in tmp.read_text().splitlines() if line.strip())
            tmp.unlink(missing_ok=True)

    all_subs.add(domain)
    state["subdomains"].update(all_subs)
    return {
        "domain": domain,
        "count": len(all_subs),
        "subdomains": sorted(all_subs)[:500],
        "sources": ["crt.sh", "subfinder", "assetfinder", "chaos", "findomain"],
    }


# ── Phase 2: Active subdomain bruteforce ─────────────────────────────────────

async def subdomain_bruteforce(domain: str, limit: int = 500, ctx: dict | None = None) -> dict:
    domain = _domain_from_target(domain)
    wordlist = resolve_wordlist("dns")
    if not wordlist:
        return {"error": "No DNS wordlist configured", "hint": "Set DNS_WORDLIST in .env"}

    words = wordlist.read_text(encoding="utf-8", errors="replace").splitlines()[:limit]
    found: set[str] = set()

    if shutil.which("dnsx"):
        # Build FQDN list
        fqdns = [f"{w.strip()}.{domain}" for w in words if w.strip() and not w.startswith("#")]
        tmp_in = WORDLIST_DIR / "_dnsx_in.txt"
        tmp_out = WORDLIST_DIR / "_dnsx_out.txt"
        tmp_in.write_text("\n".join(fqdns))
        await _run_cmd(["dnsx", "-l", str(tmp_in), "-silent", "-o", str(tmp_out)])
        if tmp_out.exists():
            found.update(line.strip() for line in tmp_out.read_text().splitlines() if line.strip())
            tmp_out.unlink(missing_ok=True)
        tmp_in.unlink(missing_ok=True)
    else:
        # Python DNS fallback (slow, limited)
        loop = asyncio.get_event_loop()
        for w in words[:100]:
            w = w.strip()
            if not w or w.startswith("#"):
                continue
            fqdn = f"{w}.{domain}"
            try:
                await loop.run_in_executor(None, socket.getaddrinfo, fqdn, None)
                found.add(fqdn)
            except socket.gaierror:
                pass

    state = _get_state(ctx)
    state["subdomains"].update(found)
    return {"domain": domain, "count": len(found), "subdomains": sorted(found)}


async def subdomain_fuzz(domain: str, ctx: dict | None = None) -> dict:
    domain = _domain_from_target(domain)
    if not shutil.which("ffuf"):
        return {"error": "ffuf not installed", "install": "go install github.com/ffuf/ffuf/v2@latest"}

    wordlist = resolve_wordlist("dns")
    if not wordlist:
        return {"error": "No DNS wordlist"}

    out_file = WORDLIST_DIR / "_ffuf_subs.json"
    await _run_cmd([
        "ffuf", "-u", f"https://FUZZ.{domain}",
        "-w", str(wordlist),
        "-mc", "200,301,302,403",
        "-t", "40",
        "-o", str(out_file), "-of", "json",
        "-s",
    ], timeout=300)

    found = []
    if out_file.exists():
        try:
            data = json.loads(out_file.read_text())
            found = [r.get("url", "") for r in data.get("results", [])]
        except json.JSONDecodeError:
            pass
        out_file.unlink(missing_ok=True)

    state = _get_state(ctx)
    for u in found:
        host = urlparse(u).hostname
        if host:
            state["subdomains"].add(host)

    return {"domain": domain, "count": len(found), "urls": found[:100]}


# ── Phase 3: Infrastructure ───────────────────────────────────────────────────

async def asn_lookup(domain: str) -> dict:
    domain = _domain_from_target(domain)
    try:
        ip = socket.gethostbyname(domain)
    except socket.gaierror as exc:
        return {"error": str(exc)}

    if shutil.which("asnmap"):
        out, _, _ = await _run_cmd(["asnmap", "-d", domain])
        return {"domain": domain, "ip": ip, "asnmap": out[:4000]}

    # Fallback: hackertarget API
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"https://api.hackertarget.com/aslookup/?q={domain}")
            return {"domain": domain, "ip": ip, "asn_info": resp.text[:2000]}
    except Exception as exc:
        return {"domain": domain, "ip": ip, "error": str(exc)}


async def reverse_dns(ip_or_cidr: str) -> dict:
    ip = ip_or_cidr.split("/")[0].strip()
    if shutil.which("dnsx"):
        proc = await asyncio.create_subprocess_exec(
            "dnsx", "-silent", "-ptr", "-resp-only",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(input=f"{ip}\n".encode()), timeout=60)
        hosts = [line.strip() for line in stdout.decode().splitlines() if line.strip()]
        return {"input": ip_or_cidr, "hosts": hosts}

    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return {"input": ip_or_cidr, "hosts": [host]}
    except socket.herror:
        return {"input": ip_or_cidr, "hosts": []}


# ── Phase 5: Alive hosts ──────────────────────────────────────────────────────

async def merge_subdomains(ctx: dict | None = None) -> dict:
    state = _get_state(ctx)
    merged = sorted(state["subdomains"])
    return {"count": len(merged), "subdomains": merged}


async def httpx_alive_check(hosts: list[str] | None = None, ctx: dict | None = None) -> dict:
    state = _get_state(ctx)
    targets = hosts or sorted(state["subdomains"])
    if not targets:
        return {"error": "No subdomains to probe", "alive": []}

    alive: list[dict] = []

    if shutil.which("httpx"):
        tmp = WORDLIST_DIR / "_httpx_in.txt"
        tmp.write_text("\n".join(targets[:1000]))
        out, _, _ = await _run_cmd([
            "httpx", "-l", str(tmp),
            "-status-code", "-title", "-web-server", "-silent",
            "-follow-redirects", "-threads", "50",
        ], timeout=300)
        tmp.unlink(missing_ok=True)
        for line in out.splitlines():
            if line.strip():
                alive.append({"raw": line.strip()})
                # Extract URL from httpx output
                url_match = re.search(r"(https?://\S+)", line)
                if url_match:
                    state["alive_hosts"].add(url_match.group(1))
    else:
        # Python fallback
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, verify=False) as client:
            sem = asyncio.Semaphore(20)

            async def probe(host: str):
                url = host if host.startswith("http") else f"https://{host}"
                async with sem:
                    try:
                        resp = await client.get(url)
                        entry = {"url": str(resp.url), "status": resp.status_code, "title": ""}
                        alive.append(entry)
                        state["alive_hosts"].add(str(resp.url))
                    except Exception:
                        try:
                            resp = await client.get(f"http://{host}")
                            entry = {"url": str(resp.url), "status": resp.status_code}
                            alive.append(entry)
                            state["alive_hosts"].add(str(resp.url))
                        except Exception:
                            pass

            await asyncio.gather(*[probe(h) for h in targets[:200]])

    return {"count": len(alive), "alive": alive[:200]}


# ── Phase 6: VHOST ────────────────────────────────────────────────────────────

async def vhost_fuzz(ip: str, domain: str, limit: int = 100, ctx: dict | None = None) -> dict:
    wordlist = resolve_wordlist("dns")
    if not wordlist or not shutil.which("ffuf"):
        return {"error": "Requires ffuf and DNS wordlist"}

    words = wordlist.read_text().splitlines()[:limit]
    tmp_wl = WORDLIST_DIR / "_vhost_wl.txt"
    tmp_wl.write_text("\n".join(words))

    out_file = WORDLIST_DIR / "_vhost_out.json"
    await _run_cmd([
        "ffuf", "-u", f"http://{ip}",
        "-w", str(tmp_wl),
        "-H", f"Host: FUZZ.{domain}",
        "-mc", "200,301,302,401,403",
        "-t", "30",
        "-o", str(out_file), "-of", "json", "-s",
    ], timeout=180)

    results = []
    if out_file.exists():
        try:
            data = json.loads(out_file.read_text())
            results = data.get("results", [])
        except json.JSONDecodeError:
            pass
        out_file.unlink(missing_ok=True)
    tmp_wl.unlink(missing_ok=True)
    return {"ip": ip, "domain": domain, "vhosts": results[:50]}


# ── Phase 7: URL discovery ────────────────────────────────────────────────────

async def wayback_urls(domain: str, ctx: dict | None = None) -> dict:
    domain = _domain_from_target(domain)
    urls: set[str] = set()
    state = _get_state(ctx)

    if shutil.which("waybackurls"):
        out, _, _ = await _run_cmd(["waybackurls", domain], timeout=120)
        urls.update(line.strip() for line in out.splitlines() if line.strip())
    elif shutil.which("gau"):
        out, _, _ = await _run_cmd(["gau", domain], timeout=120)
        urls.update(line.strip() for line in out.splitlines() if line.strip())
    else:
        # Wayback CDX API
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(
                    "https://web.archive.org/cdx/search/cdx",
                    params={"url": f"*.{domain}/*", "output": "text", "fl": "original", "collapse": "urlkey"},
                )
                if resp.status_code == 200:
                    urls.update(line.strip() for line in resp.text.splitlines() if line.strip())
        except Exception as exc:
            return {"error": str(exc), "count": 0, "urls": []}

    state["urls"].update(urls)
    return {"domain": domain, "count": len(urls), "urls": sorted(urls)[:300]}


async def crawl_urls(seed_url: str, ctx: dict | None = None) -> dict:
    state = _get_state(ctx)
    urls: set[str] = set()

    if shutil.which("katana"):
        out, _, _ = await _run_cmd([
            "katana", "-u", seed_url, "-d", "3", "-jc", "-silent", "-nc",
        ], timeout=180)
        urls.update(line.strip() for line in out.splitlines() if line.strip())
    elif shutil.which("gospider"):
        out, _, _ = await _run_cmd([
            "gospider", "-s", seed_url, "-t", "10", "-d", "2", "--sitemap", "--robots",
        ], timeout=180)
        for line in out.splitlines():
            m = re.search(r"(https?://[^\s\]]+)", line)
            if m:
                urls.add(m.group(1))
    else:
        # Basic link extraction
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as client:
                resp = await client.get(seed_url)
                links = re.findall(r'href=["\']([^"\']+)["\']', resp.text)
                base = str(resp.url)
                for link in links:
                    urls.add(urljoin(base, link))
        except Exception as exc:
            return {"error": str(exc), "urls": []}

    state["urls"].update(urls)
    return {"seed": seed_url, "count": len(urls), "urls": sorted(urls)[:200]}


URL_CATEGORIES = {
    "javascript": r"\.js(\?|$)",
    "api": r"\.(json|xml|graphql|gql)(\?|$)|/api/|/graphql",
    "auth": r"login|signin|auth|oauth|reset|password|register",
    "admin": r"admin|dashboard|internal|manage|panel",
    "upload": r"upload|file|download|image|media",
    "sensitive": r"\.(env|bak|config|sql|log|pem|key)(\?|$)",
    "idor": r"/\d{2,}|id=\d+|user_id=|account_id=",
    "redirect": r"redirect|callback|goto|return|dest=|url=|next=",
    "cloud": r"aws|s3|bucket|gcp|azure|token|apikey|secret",
}


def categorize_urls(urls: list[str] | None = None, ctx: dict | None = None) -> dict:
    state = _get_state(ctx)
    source = urls or sorted(state["urls"])
    categorized: dict[str, list[str]] = {k: [] for k in URL_CATEGORIES}

    for url in source:
        for cat, pattern in URL_CATEGORIES.items():
            if re.search(pattern, url, re.I):
                categorized[cat].append(url)

    # Deduplicate
    for cat in categorized:
        categorized[cat] = sorted(set(categorized[cat]))[:100]

    js_urls = categorized.get("javascript", [])
    state["js_urls"].update(js_urls)

    return {
        "total_urls": len(source),
        "categories": {k: {"count": len(v), "samples": v[:20]} for k, v in categorized.items() if v},
    }


# ── Phase 8: JS analysis ──────────────────────────────────────────────────────

SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]([A-Za-z0-9_\-]{16,})['\"]", "api_key"),
    (r"(?i)(secret|token|password|bearer)\s*[:=]\s*['\"]([^'\"]{8,})['\"]", "secret"),
    (r"AKIA[0-9A-Z]{16}", "aws_access_key"),
    (r"(?i)-----BEGIN (RSA |EC )?PRIVATE KEY-----", "private_key"),
    (r"ghp_[A-Za-z0-9]{36}", "github_token"),
    (r"sk_live_[A-Za-z0-9]{24,}", "stripe_key"),
    (r"(?i)firebase[a-z0-9_.-]+\.firebaseio\.com", "firebase_url"),
]


async def extract_js_urls(domain: str, ctx: dict | None = None) -> dict:
    state = _get_state(ctx)
    all_urls = sorted(state["urls"])
    js_urls = [u for u in all_urls if re.search(r"\.js(\?|$)", u, re.I) and not re.search(r"\.json", u, re.I)]
    if not js_urls and state["alive_hosts"]:
        for host in list(state["alive_hosts"])[:5]:
            result = await crawl_urls(host, ctx)
            js_urls.extend(
                u for u in result.get("urls", [])
                if re.search(r"\.js(\?|$)", u, re.I)
            )
    js_urls = sorted(set(js_urls))[:100]
    state["js_urls"].update(js_urls)
    return {"count": len(js_urls), "js_urls": js_urls}


async def js_secret_scan(js_urls: list[str] | None = None, ctx: dict | None = None) -> dict:
    state = _get_state(ctx)
    targets = js_urls or sorted(state["js_urls"])[:30]
    if not targets:
        return {"error": "No JS URLs found", "secrets": []}

    findings = []
    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        for url in targets:
            try:
                resp = await client.get(url)
                text = resp.text[:500_000]
                for pattern, kind in SECRET_PATTERNS:
                    for match in re.finditer(pattern, text):
                        findings.append({
                            "url": url,
                            "type": kind,
                            "match": match.group(0)[:120],
                            "severity": "high" if kind in ("private_key", "aws_access_key", "github_token") else "medium",
                        })
            except Exception:
                continue

    return {"scanned": len(targets), "secrets_found": len(findings), "secrets": findings[:50]}


# ── Phase 9: Directory discovery ─────────────────────────────────────────────

async def directory_fuzz(base_url: str, limit: int = 200, ctx: dict | None = None) -> dict:
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"

    wordlist = resolve_wordlist("web")
    if not wordlist:
        return {"error": "No web wordlist configured"}

    if shutil.which("ffuf"):
        words = wordlist.read_text().splitlines()[:limit]
        tmp_wl = WORDLIST_DIR / "_dir_wl.txt"
        tmp_wl.write_text("\n".join(words))
        out_file = WORDLIST_DIR / "_dir_out.json"
        await _run_cmd([
            "ffuf", "-u", f"{base_url.rstrip('/')}/FUZZ",
            "-w", str(tmp_wl),
            "-mc", "200,204,301,302,307,401,403",
            "-t", "40", "-s",
            "-o", str(out_file), "-of", "json",
        ], timeout=300)
        results = []
        if out_file.exists():
            try:
                results = json.loads(out_file.read_text()).get("results", [])
            except json.JSONDecodeError:
                pass
            out_file.unlink(missing_ok=True)
        tmp_wl.unlink(missing_ok=True)
        return {"base_url": base_url, "found": len(results), "paths": results[:50]}

    # Python fallback — check common paths
    words = wordlist.read_text().splitlines()[:50]
    found = []
    async with httpx.AsyncClient(timeout=8, follow_redirects=False, verify=False) as client:
        for w in words:
            w = w.strip()
            if not w:
                continue
            url = f"{base_url.rstrip('/')}/{w.lstrip('/')}"
            try:
                resp = await client.get(url)
                if resp.status_code in (200, 301, 302, 401, 403):
                    found.append({"url": url, "status": resp.status_code})
            except Exception:
                pass
    return {"base_url": base_url, "found": len(found), "paths": found}


async def sensitive_file_scan(domain: str, ctx: dict | None = None) -> dict:
    state = _get_state(ctx)
    urls = sorted(state["urls"])
    pattern = re.compile(
        r"\.(xls|xlsx|csv|sql|db|bak|backup|old|tar\.gz|zip|pdf|pem|key|crt|env|json|yml|yaml|conf|config|git|htpasswd|log|DS_Store)(\?|$)",
        re.I,
    )
    sensitive = [u for u in urls if pattern.search(u)]
    return {"domain": domain, "count": len(sensitive), "files": sensitive[:100]}


# ── Phase 10: GitHub intel ────────────────────────────────────────────────────

async def github_recon(domain: str) -> dict:
    if not settings.github_token:
        return {
            "error": "GITHUB_TOKEN not set",
            "hint": "Add GITHUB_TOKEN to .env for GitHub recon",
            "manual_dorks": [
                f'"{domain}" filename:.env',
                f'"{domain}" extension:json api_key',
                f'org:{domain.split(".")[0]} password',
            ],
        }

    results = []
    queries = [
        f"{domain} filename:.env",
        f"{domain} extension:json secret",
        f"{domain} api_key OR apikey OR token",
    ]
    headers = {"Authorization": f"token {settings.github_token}", "Accept": "application/vnd.github+json"}

    async with httpx.AsyncClient(timeout=30) as client:
        for q in queries:
            try:
                resp = await client.get(
                    "https://api.github.com/search/code",
                    params={"q": q, "per_page": 5},
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", []):
                        results.append({
                            "repo": item.get("repository", {}).get("full_name"),
                            "path": item.get("path"),
                            "url": item.get("html_url"),
                            "query": q,
                        })
            except Exception:
                continue

    return {"domain": domain, "count": len(results), "results": results}


# ── Phase 11: Port scan ───────────────────────────────────────────────────────

async def port_scan(hosts: list[str] | None = None, ctx: dict | None = None) -> dict:
    state = _get_state(ctx)
    targets = hosts or list(state.get("ips") or [])[:20]
    if not targets and state["subdomains"]:
        for sub in list(state["subdomains"])[:10]:
            try:
                ip = socket.gethostbyname(sub)
                targets.append(ip)
                state["ips"].add(ip)
            except socket.gaierror:
                pass

    if not targets:
        return {"error": "No IPs to scan"}

    if shutil.which("naabu"):
        tmp = WORDLIST_DIR / "_naabu_in.txt"
        tmp.write_text("\n".join(set(targets)))
        out, _, _ = await _run_cmd([
            "naabu", "-list", str(tmp), "-top-ports", "1000", "-silent", "-rate", "1000",
        ], timeout=300)
        tmp.unlink(missing_ok=True)
        ports = [l.strip() for l in out.splitlines() if l.strip()]
        return {"hosts_scanned": len(set(targets)), "open_ports": ports[:200]}

    # nmap fallback on first host
    if shutil.which("nmap") and targets:
        out, _, _ = await _run_cmd(["nmap", "-sV", "-T4", "-F", targets[0]], timeout=120)
        return {"host": targets[0], "output": out[:6000]}

    return {"error": "Install naabu or nmap for port scanning"}


# ── Phase 12: Nuclei exposures ────────────────────────────────────────────────

async def run_nuclei_exposures(url: str) -> dict:
    if not shutil.which("nuclei"):
        return {"error": "nuclei not installed"}
    out, _, _ = await _run_cmd([
        "nuclei", "-u", url,
        "-t", "http/exposures/",
        "-severity", "critical,high,medium",
        "-silent", "-jsonl",
    ], timeout=180)
    findings = []
    for line in out.splitlines():
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return {"url": url, "count": len(findings), "findings": findings[:30]}


# ── Phase 13: Subdomain takeover ─────────────────────────────────────────────

TAKEOVER_CNAMEs = [
    "github.io", "herokuapp.com", "herokussl.com", "azurewebsites.net",
    "cloudfront.net", "s3.amazonaws.com", "zendesk.com", "fastly.net",
    "pantheonsite.io", "ghost.io", "surge.sh", "bitbucket.io",
    "wordpress.com", "teamwork.com", "helpjuice.com", "helpscoutdocs.com",
    "cargocollective.com", "statuspage.io", "uservoice.com", "smartling.com",
]


async def subdomain_takeover_check(subdomains: list[str] | None = None, ctx: dict | None = None) -> dict:
    state = _get_state(ctx)
    targets = subdomains or sorted(state["subdomains"])[:200]
    candidates = []

    if shutil.which("subzy"):
        tmp = WORDLIST_DIR / "_subzy_in.txt"
        tmp.write_text("\n".join(targets))
        out, _, _ = await _run_cmd(["subzy", "run", "--targets", str(tmp), "--hide_fails"], timeout=300)
        tmp.unlink(missing_ok=True)
        vuln_lines = [l for l in out.splitlines() if "vulnerable" in l.lower() or "taken" in l.lower()]
        return {"scanned": len(targets), "vulnerable": vuln_lines[:50], "raw": out[:3000]}

    # Python CNAME check (requires dnspython)
    try:
        import dns.resolver
        for sub in targets[:100]:
            try:
                answers = dns.resolver.resolve(sub, "CNAME")
                for rdata in answers:
                    cname = str(rdata.target).lower()
                    for pattern in TAKEOVER_CNAMEs:
                        if pattern in cname:
                            candidates.append({"subdomain": sub, "cname": cname, "service": pattern})
            except Exception:
                continue
    except ImportError:
        return {
            "scanned": len(targets),
            "candidates": [],
            "hint": "Install dnspython or subzy for CNAME takeover checks",
        }

    return {"scanned": len(targets), "candidates": candidates[:50]}


# ── RAG enrichment ────────────────────────────────────────────────────────────

async def enrich_with_rag(vuln_type: str, technology: str = "") -> dict:
    from app.services.rag_service import rag_service
    from app.tools.web_search import google_search

    query = f"{vuln_type} vulnerability exploitation remediation {technology}".strip()
    chunks = rag_service.retrieve(query, top_k=5)
    web = await google_search(f"{vuln_type} {technology} CVE bug bounty 2025 2026", 3)
    return {
        "query": query,
        "knowledge_base": [{"content": c.content[:400], "score": c.score} for c in chunks],
        "web_results": web,
    }


# ── Methodology pipeline runner ───────────────────────────────────────────────

async def run_methodology_pipeline(
    domain: str,
    phases: list[str] | None = None,
    ctx: dict | None = None,
) -> dict:
    from app.tools.methodology import DEFAULT_PIPELINE, PHASE_BY_NAME

    domain = _domain_from_target(domain)
    phase_names = phases or DEFAULT_PIPELINE
    results: dict[str, Any] = {"domain": domain, "phases": {}}

    phase_runners = {
        "passive_subdomain_enum": lambda: passive_subdomain_enum(domain, ctx),
        "certificate_transparency": lambda: certificate_transparency(domain),
        "active_subdomain_enum": lambda: subdomain_bruteforce(domain, ctx=ctx),
        "subdomain_bruteforce": lambda: subdomain_bruteforce(domain, ctx=ctx),
        "subdomain_fuzz": lambda: subdomain_fuzz(domain, ctx),
        "infrastructure_mapping": lambda: asn_lookup(domain),
        "asn_lookup": lambda: asn_lookup(domain),
        "alive_host_detection": lambda: httpx_alive_check(ctx=ctx),
        "merge_subdomains": lambda: merge_subdomains(ctx),
        "url_endpoint_discovery": lambda: wayback_urls(domain, ctx),
        "wayback_urls": lambda: wayback_urls(domain, ctx),
        "crawl_urls": lambda: crawl_urls(f"https://{domain}", ctx),
        "categorize_urls": None,  # sync — handled below
        "js_analysis": lambda: extract_js_urls(domain, ctx),
        "extract_js_urls": lambda: extract_js_urls(domain, ctx),
        "js_secret_scan": lambda: js_secret_scan(ctx=ctx),
        "directory_discovery": lambda: directory_fuzz(f"https://{domain}", ctx=ctx),
        "directory_fuzz": lambda: directory_fuzz(f"https://{domain}", ctx=ctx),
        "sensitive_file_scan": lambda: sensitive_file_scan(domain, ctx),
        "github_intel": lambda: github_recon(domain),
        "github_recon": lambda: github_recon(domain),
        "port_scanning": lambda: port_scan(ctx=ctx),
        "port_scan": lambda: port_scan(ctx=ctx),
        "vuln_scanning": lambda: run_nuclei_exposures(f"https://{domain}"),
        "subdomain_takeover": lambda: subdomain_takeover_check(ctx=ctx),
        "subdomain_takeover_check": lambda: subdomain_takeover_check(ctx=ctx),
    }

    for name in phase_names:
        runner = phase_runners.get(name)
        if name == "categorize_urls":
            try:
                results["phases"][name] = categorize_urls(ctx=ctx)
            except Exception as exc:
                results["phases"][name] = {"error": str(exc)}
            continue
        if not runner:
            results["phases"][name] = {"skipped": True, "reason": "No runner"}
            continue
        try:
            results["phases"][name] = await runner()
        except Exception as exc:
            results["phases"][name] = {"error": str(exc)}

    state = _get_state(ctx)
    results["summary"] = {
        "subdomains": len(state["subdomains"]),
        "alive_hosts": len(state["alive_hosts"]),
        "urls": len(state["urls"]),
        "js_urls": len(state["js_urls"]),
    }
    return results
