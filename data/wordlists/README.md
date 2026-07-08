# Wordlists for Bug Bounty Recon

CypherMind uses wordlists for DNS subdomain bruteforce, directory fuzzing, and parameter discovery.

## Quick setup

### Option 1 — Bundled defaults (no install)

Built-in minimal wordlists are auto-created at:

- `data/wordlists/dns/subdomains-top1000.txt` (~80 common subdomains)
- `data/wordlists/web/common-dirs.txt` (~40 common paths)

These work out of the box for demos; use SecLists for real hunts.

### Option 2 — SecLists (recommended)

```bash
# macOS / Linux
sudo git clone https://github.com/danielmiessler/SecLists /usr/share/seclists

# Or user install
git clone https://github.com/danielmiessler/SecLists ~/SecLists
```

Add to `.env`:

```bash
DNS_WORDLIST=/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt
WEB_WORDLIST=/usr/share/seclists/Discovery/Web-Content/common.txt
PARAMS_WORDLIST=/usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt
```

### Option 3 — Upload via UI or API

Upload wordlists in the **Bug Bounty → Wordlists** section, or:

```bash
curl -F "file=@subdomains.txt" http://localhost:8000/api/v1/wordlists/upload/dns
```

Then set the returned path in `.env`.

## API keys (optional, improves passive recon)

```bash
GITHUB_TOKEN=ghp_...          # GitHub code search (Phase 10)
PDCP_API_KEY=...              # ProjectDiscovery Chaos dataset (Phase 1)
```

## External CLI tools (optional)

Tools degrade gracefully to Python/API fallbacks when not installed:

| Tool | Phase | Install |
|------|-------|---------|
| subfinder, httpx, dnsx, nuclei | 1,5,12 | `go install -v github.com/projectdiscovery/...` |
| ffuf | 2,6,9 | `go install github.com/ffuf/ffuf/v2@latest` |
| waybackurls, gau | 7 | `go install github.com/tomnomnom/waybackurls@latest` |
| naabu, nmap | 11 | ProjectDiscovery / system package |
| subzy | 13 | `go install github.com/PentestPad/subzy@latest` |

Check status: `GET /api/v1/wordlists/status` or use the `wordlist_status` agent tool.
