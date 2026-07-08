"""Wordlist path resolution for recon/bruteforce."""
from __future__ import annotations

from pathlib import Path

from app.core.config import PROJECT_ROOT, get_settings

WORDLIST_DIR = PROJECT_ROOT / "data" / "wordlists"
WORDLIST_DIR.mkdir(parents=True, exist_ok=True)
DNS_DIR = WORDLIST_DIR / "dns"
WEB_DIR = WORDLIST_DIR / "web"
PARAMS_DIR = WORDLIST_DIR / "params"
for _d in (DNS_DIR, WEB_DIR, PARAMS_DIR):
    _d.mkdir(exist_ok=True)

# Bundled minimal wordlists (fallback when seclists not installed)
BUILTIN_DNS = DNS_DIR / "subdomains-top1000.txt"
BUILTIN_WEB = WEB_DIR / "common-dirs.txt"

DEFAULT_DNS_WORDS = [
    "www", "mail", "ftp", "localhost", "webmail", "smtp", "pop", "ns1", "ns2",
    "admin", "api", "dev", "staging", "stage", "test", "beta", "demo", "portal",
    "vpn", "remote", "git", "gitlab", "jenkins", "ci", "cdn", "static", "assets",
    "app", "mobile", "m", "internal", "intranet", "secure", "auth", "login",
    "dashboard", "panel", "backup", "db", "database", "redis", "mongo", "elastic",
    "kibana", "grafana", "prometheus", "docs", "wiki", "help", "support", "status",
    "old", "new", "legacy", "sandbox", "uat", "preprod", "prod", "production",
    "graphql", "ws", "websocket", "socket", "stream", "media", "upload", "files",
    "s3", "storage", "blob", "pay", "payment", "billing", "shop", "store", "cart",
]

DEFAULT_WEB_WORDS = [
    ".env", ".git", "admin", "api", "backup", "config", "debug", "console",
    "swagger", "graphql", "actuator", "health", "metrics", "status", "login",
    "register", "upload", "download", "robots.txt", "sitemap.xml", ".well-known",
    "wp-admin", "wp-login.php", "phpinfo.php", "server-status", "trace", "test",
    "staging", "dev", "internal", "private", "secret", "credentials", "keys",
]


def ensure_builtin_wordlists():
    if not BUILTIN_DNS.exists():
        BUILTIN_DNS.write_text("\n".join(DEFAULT_DNS_WORDS) + "\n")
    if not BUILTIN_WEB.exists():
        BUILTIN_WEB.write_text("\n".join(DEFAULT_WEB_WORDS) + "\n")


ensure_builtin_wordlists()


def resolve_wordlist(kind: str) -> Path | None:
    """kind: dns | web | params"""
    settings = get_settings()
    env_map = {
        "dns": settings.dns_wordlist,
        "web": settings.web_wordlist,
        "params": settings.params_wordlist,
    }
    path_str = env_map.get(kind, "")
    if path_str:
        p = Path(path_str).expanduser()
        if p.exists():
            return p

    defaults = {"dns": BUILTIN_DNS, "web": BUILTIN_WEB, "params": PARAMS_DIR / "common-params.txt"}
    p = defaults.get(kind)
    if p and p.exists():
        return p

    # Try common seclists locations
    seclists = {
        "dns": [
            "/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt",
            "/usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-110000.txt",
        ],
        "web": [
            "/usr/share/seclists/Discovery/Web-Content/common.txt",
            "/usr/share/wordlists/seclists/Discovery/Web-Content/common.txt",
        ],
    }
    for candidate in seclists.get(kind, []):
        if Path(candidate).exists():
            return Path(candidate)
    return defaults.get(kind)


def wordlist_status() -> dict:
    dns = resolve_wordlist("dns")
    web = resolve_wordlist("web")
    params = resolve_wordlist("params")
    return {
        "dns_wordlist": str(dns) if dns else None,
        "dns_lines": _count_lines(dns),
        "web_wordlist": str(web) if web else None,
        "web_lines": _count_lines(web),
        "params_wordlist": str(params) if params else None,
        "params_lines": _count_lines(params),
        "wordlist_dir": str(WORDLIST_DIR),
        "seclists_detected": any(
            Path(p).exists()
            for p in [
                "/usr/share/seclists",
                "/usr/share/wordlists/seclists",
            ]
        ),
    }


def _count_lines(path: Path | None) -> int:
    if not path or not path.exists():
        return 0
    try:
        return sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
    except OSError:
        return 0
