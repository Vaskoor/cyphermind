"""Unit tests for report generation."""
from app.services.report_service import (
    extract_recon_from_tool_outputs,
    generate_agent_html_report,
    generate_recon_html_report,
)


def test_extract_recon_from_methodology_pipeline():
    tool_outputs = {
        "methodology_pipeline": {
            "domain": "example.com",
            "summary": {"subdomains": 5, "alive_hosts": 2, "urls": 100, "js_urls": 10},
            "phases": {
                "passive_subdomain_enum": {
                    "count": 5,
                    "subdomains": ["www.example.com", "api.example.com"],
                },
                "wayback_urls": {
                    "count": 3,
                    "urls": ["https://example.com/login", "https://example.com/admin"],
                },
            },
        },
        "final_answer": "Found 1 medium issue on staging subdomain.",
    }
    recon = extract_recon_from_tool_outputs("BugBountyAgent", tool_outputs)
    assert recon["stats"]["Subdomains"] == 5
    assert recon["executive_summary"] == "Found 1 medium issue on staging subdomain."
    assert any(s["title"] == "Discovered Subdomains" for s in recon["sections"])


def test_generate_recon_html_report():
    html = generate_recon_html_report(
        "Test Engagement",
        "BugBountyAgent",
        {"url": "https://example.com"},
        {
            "methodology_pipeline": {
                "summary": {"subdomains": 3, "alive_hosts": 1, "urls": 10, "js_urls": 2},
                "phases": {},
            }
        },
    )
    assert "Recon Report" in html
    assert "example.com" in html
    assert "Subdomains" in html


def test_generate_agent_html_with_findings():
    html = generate_agent_html_report(
        "Test Engagement",
        "ReconAgent",
        {"url": "https://example.com"},
        [{"title": "Open port 22", "severity": "high", "description": "SSH exposed", "confidence": 0.9}],
        {"nmap": "22/tcp open ssh"},
    )
    assert "Open port 22" in html
    assert "ReconAgent" in html
