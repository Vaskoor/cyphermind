"""Web search: Google Custom Search API with DuckDuckGo fallback."""
from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def google_search(query: str, num_results: int = 5) -> list[dict]:
    """Search via Google Custom Search API or DuckDuckGo fallback."""
    num_results = min(max(num_results, 1), 10)
    query = query.strip()
    if not query:
        return []

    if settings.google_api_key and settings.google_cse_id:
        return await _google_cse_search(query, num_results)

    return await _duckduckgo_search(query, num_results)


async def _google_cse_search(query: str, num: int) -> list[dict]:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": settings.google_api_key,
        "cx": settings.google_cse_id,
        "q": query,
        "num": num,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("items", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "source": "google",
        })
    return results


async def _duckduckgo_search(query: str, num: int) -> list[dict]:
    """DuckDuckGo HTML lite fallback — no API key required."""
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                    "source": "duckduckgo",
                })
        return results
    except ImportError:
        logger.warning("duckduckgo-search not installed; using httpx lite scrape")
        return await _ddg_lite_scrape(query, num)


async def _ddg_lite_scrape(query: str, num: int) -> list[dict]:
    """Minimal DDG lite HTML parse fallback."""
    url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "CypherMind/1.0"})
        resp.raise_for_status()
        html = resp.text

    results = []
    # DDG lite: links in <a class="result-link">
    link_pattern = re.compile(
        r'<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
        re.IGNORECASE,
    )
    snippet_pattern = re.compile(
        r'<td class="result-snippet"[^>]*>([^<]+)</td>',
        re.IGNORECASE,
    )
    links = link_pattern.findall(html)
    snippets = snippet_pattern.findall(html)

    for i, (href, title) in enumerate(links[:num]):
        results.append({
            "title": title.strip(),
            "url": href,
            "snippet": snippets[i].strip() if i < len(snippets) else "",
            "source": "duckduckgo_lite",
        })
    return results
