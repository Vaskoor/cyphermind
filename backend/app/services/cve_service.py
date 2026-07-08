"""CVE lookup via NVD API with in-memory cache."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_cache: dict[str, dict[str, Any]] = {}


async def lookup_cve(cve_id: str) -> dict[str, Any]:
    cve_id = cve_id.upper().strip()
    if cve_id in _cache:
        return _cache[cve_id]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(NVD_API_URL, params={"cveId": cve_id})
        resp.raise_for_status()
        data = resp.json()

    vulns = data.get("vulnerabilities", [])
    if not vulns:
        result: dict[str, Any] = {"cve_id": cve_id, "found": False}
    else:
        cve = vulns[0]["cve"]
        descriptions = [
            d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"
        ]
        metrics = cve.get("metrics", {})
        cvss = None
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if key in metrics and metrics[key]:
                cvss = metrics[key][0].get("cvssData", {})
                break
        result = {
            "cve_id": cve_id,
            "found": True,
            "description": descriptions[0] if descriptions else "",
            "published": cve.get("published"),
            "cvss": cvss,
            "cwe_ids": [
                w.get("description", [{}])[0].get("value")
                for w in cve.get("weaknesses", [])
            ],
        }

    _cache[cve_id] = result
    return result
