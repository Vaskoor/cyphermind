"""Report generation: HTML, JSON, SARIF, recon, and per-agent reports."""
from __future__ import annotations

import html
import json
from datetime import datetime
from typing import Any

from jinja2 import BaseLoader, Environment

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>CypherMind Security Report — {{ engagement_name }}</title>
  <style>
    body { font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; margin: 0; padding: 2rem; max-width: 1100px; }
    h1 { color: #60a5fa; border-bottom: 2px solid #1e40af; padding-bottom: .5rem; }
    h2 { color: #93c5fd; margin-top: 2rem; }
    h3 { color: #bfdbfe; }
    .finding { background: #1e293b; border-left: 4px solid #3b82f6; padding: 1rem; margin: 1rem 0; border-radius: 4px; }
    .critical { border-color: #ef4444; }
    .high { border-color: #f97316; }
    .medium { border-color: #eab308; }
    .low { border-color: #22c55e; }
    .badge { display: inline-block; padding: .2rem .6rem; border-radius: 999px; font-size: .75rem; font-weight: bold; margin-left: .5rem; }
    .badge-critical { background: #ef4444; }
    .badge-high { background: #f97316; }
    .badge-medium { background: #eab308; color: #000; }
    .badge-low { background: #22c55e; color: #000; }
    .badge-recon { background: #3b82f6; }
    .badge-info { background: #64748b; }
    .meta { color: #94a3b8; font-size: .85rem; }
    table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
    th { background: #1e40af; color: #fff; padding: .5rem; text-align: left; }
    td { padding: .5rem; border-bottom: 1px solid #334155; vertical-align: top; }
    pre { background: #0f172a; padding: 1rem; border-radius: 4px; overflow-x: auto; font-size: .8rem; white-space: pre-wrap; word-break: break-word; }
    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0; }
    .stat { background: #1e293b; padding: 1rem; border-radius: 8px; text-align: center; }
    .stat-val { font-size: 1.75rem; font-weight: bold; color: #60a5fa; }
    .stat-label { font-size: .75rem; color: #94a3b8; text-transform: uppercase; }
    .section { background: #1e293b; border-radius: 8px; padding: 1.25rem; margin: 1rem 0; }
    ul.urls { max-height: 300px; overflow-y: auto; font-size: .85rem; }
    ul.urls li { margin: .25rem 0; word-break: break-all; }
    .summary-box { background: #172554; border: 1px solid #1e40af; padding: 1.25rem; border-radius: 8px; line-height: 1.6; }
  </style>
</head>
<body>
  <h1>🛡️ CypherMind Security Report</h1>
  <p class="meta">
    Engagement: <strong>{{ engagement_name }}</strong> |
    Agent: <strong>{{ agent_name }}</strong> |
    Type: <span class="badge badge-recon">{{ report_type|upper }}</span> |
    Generated: {{ generated_at }}
  </p>

  {% if executive_summary %}
  <h2>Executive Summary</h2>
  <div class="summary-box">{{ executive_summary }}</div>
  {% endif %}

  {% if recon_stats %}
  <h2>Recon Intelligence</h2>
  <div class="stat-grid">
    {% for label, val in recon_stats.items() %}
    <div class="stat"><div class="stat-val">{{ val }}</div><div class="stat-label">{{ label }}</div></div>
    {% endfor %}
  </div>
  {% endif %}

  {% for section in recon_sections %}
  <div class="section">
    <h3>{{ section.title }} <span class="badge badge-info">{{ section.count }} items</span></h3>
    {% if section.entries %}
    <ul class="urls">
      {% for item in section.entries[:50] %}
      <li>{{ item }}</li>
      {% endfor %}
    </ul>
    {% if section.entries|length > 50 %}<p class="meta">… and {{ section.entries|length - 50 }} more</p>{% endif %}
    {% else %}
    <p class="meta">No data collected for this section.</p>
    {% endif %}
    {% if section.detail %}
    <pre>{{ section.detail }}</pre>
    {% endif %}
  </div>
  {% endfor %}

  {% if phase_details %}
  <h2>Methodology Phases</h2>
  {% for phase in phase_details %}
  <div class="section">
    <h3>{{ phase.name }}</h3>
    <pre>{{ phase.summary }}</pre>
  </div>
  {% endfor %}
  {% endif %}

  <h2>Findings Summary</h2>
  <table>
    <tr><th>Severity</th><th>Count</th></tr>
    <tr><td>Critical</td><td>{{ summary.critical }}</td></tr>
    <tr><td>High</td><td>{{ summary.high }}</td></tr>
    <tr><td>Medium</td><td>{{ summary.medium }}</td></tr>
    <tr><td>Low</td><td>{{ summary.low }}</td></tr>
    <tr><td>Info</td><td>{{ summary.info }}</td></tr>
  </table>

  <h2>Vulnerability Findings</h2>
  {% if findings %}
  {% for f in findings %}
  <div class="finding {{ f.severity }}">
    <strong>{{ loop.index }}. {{ f.title }}</strong>
    <span class="badge badge-{{ f.severity }}">{{ f.severity|upper }}</span>
    <p>{{ f.description }}</p>
    {% if f.cwe_id %}<p class="meta">CWE: {{ f.cwe_id }}</p>{% endif %}
    {% if f.cve_id %}<p class="meta">CVE: {{ f.cve_id }}</p>{% endif %}
    {% if f.file_path %}<p class="meta">File: {{ f.file_path }}{% if f.line_number %} line {{ f.line_number }}{% endif %}</p>{% endif %}
    {% if f.payload %}<pre>{{ f.payload }}</pre>{% endif %}
    <p class="meta">Confidence: {{ (f.confidence * 100)|int }}%</p>
  </div>
  {% endfor %}
  {% else %}
  <p class="meta">No confirmed vulnerabilities reported by this agent.</p>
  {% endif %}

  <footer style="color:#475569;margin-top:2rem;font-size:.8rem;">
    Generated by CypherMind AI Penetration Testing Copilot · {{ agent_name }}
  </footer>
</body>
</html>
"""

RECON_ONLY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Recon Report — {{ target_name }}</title>
  <style>
    body { font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e2e8f0; margin: 0; padding: 2rem; max-width: 1100px; }
    h1 { color: #22d3ee; border-bottom: 2px solid #0891b2; padding-bottom: .5rem; }
    h2 { color: #67e8f9; margin-top: 2rem; }
    h3 { color: #a5f3fc; }
    .meta { color: #94a3b8; font-size: .85rem; }
    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0; }
    .stat { background: #1e293b; padding: 1rem; border-radius: 8px; text-align: center; }
    .stat-val { font-size: 1.75rem; font-weight: bold; color: #22d3ee; }
    .stat-label { font-size: .75rem; color: #94a3b8; text-transform: uppercase; }
    .section { background: #1e293b; border-radius: 8px; padding: 1.25rem; margin: 1rem 0; }
    pre { background: #0f172a; padding: 1rem; border-radius: 4px; overflow-x: auto; font-size: .8rem; white-space: pre-wrap; }
    ul.urls { max-height: 400px; overflow-y: auto; font-size: .85rem; }
    ul.urls li { margin: .25rem 0; word-break: break-all; }
    .badge { display: inline-block; padding: .2rem .6rem; border-radius: 999px; font-size: .75rem; background: #0891b2; }
  </style>
</head>
<body>
  <h1>🔍 CypherMind Recon Report</h1>
  <p class="meta">
    Target: <strong>{{ target_name }}</strong> |
    Agent: <strong>{{ agent_name }}</strong> |
    Generated: {{ generated_at }}
  </p>

  {% if recon_stats %}
  <div class="stat-grid">
    {% for label, val in recon_stats.items() %}
    <div class="stat"><div class="stat-val">{{ val }}</div><div class="stat-label">{{ label }}</div></div>
    {% endfor %}
  </div>
  {% endif %}

  {% for section in recon_sections %}
  <div class="section">
    <h3>{{ section.title }} <span class="badge">{{ section.count }}</span></h3>
    {% if section.entries %}
    <ul class="urls">
      {% for item in section.entries[:100] %}
      <li>{{ item }}</li>
      {% endfor %}
    </ul>
    {% if section.entries|length > 100 %}<p class="meta">… and {{ section.entries|length - 100 }} more</p>{% endif %}
    {% endif %}
    {% if section.detail %}<pre>{{ section.detail }}</pre>{% endif %}
  </div>
  {% endfor %}

  {% if phase_details %}
  <h2>Phase Results</h2>
  {% for phase in phase_details %}
  <div class="section">
    <h3>{{ phase.name }}</h3>
    <pre>{{ phase.summary }}</pre>
  </div>
  {% endfor %}
  {% endif %}

  <footer style="color:#475569;margin-top:2rem;font-size:.8rem;">
    CypherMind Recon Intelligence Report
  </footer>
</body>
</html>
"""


def _severity_summary(findings: list[dict]) -> dict:
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        sev = f.get("severity", "info").lower()
        summary[sev] = summary.get(sev, 0) + 1
    return summary


def _esc(text: Any) -> str:
    return html.escape(str(text)) if text is not None else ""


def extract_recon_from_tool_outputs(agent_name: str, tool_outputs: dict) -> dict:
    """Build structured recon data from agent tool_outputs."""
    recon: dict[str, Any] = {
        "stats": {},
        "sections": [],
        "phase_details": [],
        "executive_summary": "",
    }

    if not tool_outputs:
        return recon

    recon["executive_summary"] = tool_outputs.get("final_answer") or ""

    pipeline = tool_outputs.get("methodology_pipeline") or {}
    if isinstance(pipeline, dict):
        summary = pipeline.get("summary") or tool_outputs.get("recon_summary") or {}
        if summary:
            recon["stats"] = {
                "Subdomains": summary.get("subdomains", 0),
                "Alive Hosts": summary.get("alive_hosts", 0),
                "URLs": summary.get("urls", 0),
                "JS Files": summary.get("js_urls", 0),
            }

        phases = pipeline.get("phases") or {}
        subdomains: list[str] = []
        alive: list[str] = []
        urls: list[str] = []
        js_urls: list[str] = []
        secrets: list[str] = []
        takeover: list[str] = []
        nuclei: list[str] = []

        for phase_name, phase_data in phases.items():
            if not isinstance(phase_data, dict):
                continue
            phase_summary = _summarize_phase(phase_name, phase_data)
            if phase_summary:
                recon["phase_details"].append({"name": phase_name, "summary": phase_summary})

            subs = phase_data.get("subdomains") or []
            if isinstance(subs, list):
                subdomains.extend(str(s) for s in subs)
            for item in phase_data.get("alive") or []:
                if isinstance(item, dict):
                    alive.append(item.get("raw") or item.get("url") or str(item))
                else:
                    alive.append(str(item))
            urls.extend(str(u) for u in (phase_data.get("urls") or [])[:200])
            js_urls.extend(str(u) for u in (phase_data.get("js_urls") or []))
            for sec in phase_data.get("secrets") or []:
                if isinstance(sec, dict):
                    secrets.append(f"{sec.get('type', 'secret')} @ {sec.get('url', '?')}: {str(sec.get('match', ''))[:80]}")
            for c in phase_data.get("candidates") or phase_data.get("vulnerable") or []:
                takeover.append(str(c))
            for f in phase_data.get("findings") or []:
                if isinstance(f, dict):
                    nuclei.append(f.get("info", {}).get("name") or str(f)[:120])
                else:
                    nuclei.append(str(f)[:120])

        if subdomains:
            recon["sections"].append({"title": "Discovered Subdomains", "count": len(subdomains), "entries": sorted(set(subdomains))})
        if alive:
            recon["sections"].append({"title": "Alive Hosts", "count": len(alive), "entries": alive})
        if urls:
            recon["sections"].append({"title": "Discovered URLs", "count": len(urls), "entries": sorted(set(urls))[:300]})
        if js_urls:
            recon["sections"].append({"title": "JavaScript Files", "count": len(js_urls), "entries": sorted(set(js_urls))})
        if secrets:
            recon["sections"].append({"title": "Potential Secrets in JS", "count": len(secrets), "entries": secrets})
        if takeover:
            recon["sections"].append({"title": "Subdomain Takeover Candidates", "count": len(takeover), "entries": takeover})
        if nuclei:
            recon["sections"].append({"title": "Nuclei / Scanner Hits", "count": len(nuclei), "entries": nuclei})

    # ReconAgent outputs
    if agent_name == "ReconAgent":
        nmap = tool_outputs.get("nmap")
        if nmap and isinstance(nmap, str) and "not installed" not in nmap:
            recon["sections"].append({"title": "Nmap Scan", "count": nmap.count("open"), "entries": [], "detail": nmap[:8000]})
        subs = tool_outputs.get("subfinder")
        if subs and isinstance(subs, str) and "not installed" not in subs:
            sub_list = [l.strip() for l in subs.splitlines() if l.strip()]
            recon["sections"].append({"title": "Subfinder Subdomains", "count": len(sub_list), "entries": sub_list})
            recon["stats"]["Subdomains"] = len(sub_list)

    briefing = tool_outputs.get("recon_briefing") or (pipeline.get("briefing") if isinstance(pipeline, dict) else None)
    if briefing and not recon["phase_details"]:
        recon["sections"].append({"title": "Recon Briefing", "count": 1, "entries": [], "detail": str(briefing)[:12000]})

    return recon


def _summarize_phase(name: str, data: dict) -> str:
    if data.get("error"):
        return f"Error: {data['error']}"
    if data.get("skipped"):
        return f"Skipped: {data.get('reason', '')}"
    parts = []
    for key in ("count", "scanned", "found", "hosts_scanned"):
        if key in data:
            parts.append(f"{key}: {data[key]}")
    for key in ("subdomains", "urls", "secrets", "candidates", "vulnerable", "open_ports"):
        val = data.get(key)
        if isinstance(val, list) and val:
            preview = ", ".join(str(v)[:60] for v in val[:8])
            parts.append(f"{key} ({len(val)}): {preview}")
    return "\n".join(parts)[:2000] if parts else json.dumps(data, default=str)[:1500]


def generate_agent_html_report(
    engagement_name: str,
    agent_name: str,
    target: dict,
    findings: list[dict],
    tool_outputs: dict | None = None,
    report_type: str = "combined",
) -> str:
    env = Environment(loader=BaseLoader())
    recon = extract_recon_from_tool_outputs(agent_name, tool_outputs or {})
    target_name = target.get("url") or target.get("name") or target.get("ip_address") or "Unknown"

    ctx = {
        "engagement_name": engagement_name,
        "agent_name": agent_name,
        "target_name": target_name,
        "report_type": report_type,
        "findings": findings,
        "summary": _severity_summary(findings),
        "recon_stats": recon.get("stats") or {},
        "recon_sections": recon.get("sections") or [],
        "phase_details": recon.get("phase_details") or [],
        "executive_summary": recon.get("executive_summary") or "",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }

    if report_type == "recon":
        tpl = env.from_string(RECON_ONLY_TEMPLATE)
        return tpl.render(**ctx)

    tpl = env.from_string(HTML_TEMPLATE)
    return tpl.render(**ctx)


def generate_recon_html_report(
    engagement_name: str,
    agent_name: str,
    target: dict,
    tool_outputs: dict,
) -> str:
    return generate_agent_html_report(
        engagement_name, agent_name, target, [], tool_outputs, report_type="recon"
    )


def generate_html_report(engagement_name: str, findings: list[dict]) -> str:
    env = Environment(loader=BaseLoader())
    tpl = env.from_string(HTML_TEMPLATE)
    return tpl.render(
        engagement_name=engagement_name,
        agent_name="All Agents",
        report_type="findings",
        findings=findings,
        summary=_severity_summary(findings),
        recon_stats={},
        recon_sections=[],
        phase_details=[],
        executive_summary="",
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )


def generate_sarif_report(engagement_name: str, findings: list[dict]) -> dict:
    """Generate SARIF 2.1.0 compliant output."""
    rules = {}
    results = []
    for f in findings:
        rule_id = f.get("cwe_id") or f.get("title", "unknown").replace(" ", "_")
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": f.get("title", rule_id),
                "shortDescription": {"text": f.get("description", "")[:256]},
            }
        result = {
            "ruleId": rule_id,
            "level": {"critical": "error", "high": "error", "medium": "warning", "low": "note"}.get(
                f.get("severity", "info"), "note"
            ),
            "message": {"text": f.get("description", "")},
        }
        if f.get("file_path"):
            result["locations"] = [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f["file_path"]},
                    "region": {"startLine": f.get("line_number", 1)},
                }
            }]
        results.append(result)

    return {
        "version": "2.1.0",
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0.json",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CypherMind",
                    "version": "1.0.0",
                    "rules": list(rules.values()),
                }
            },
            "results": results,
        }],
    }
