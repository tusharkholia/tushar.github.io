"""Automated deal research and extraction pipeline for PE Lens."""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

import aiohttp
import feedparser
import trafilatura
from duckduckgo_search import DDGS
from openai import OpenAI

from config import settings


@dataclass
class SourceItem:
    title: str
    url: str
    outlet: str
    published: str | None
    snippet: str
    content: str


@dataclass
class DealRecord:
    date: str
    target: str
    acquirer: str
    deal_size: str
    valuation_multiple: str
    strategic_rationale: str
    revenue: str
    buyer_type: str
    sector: str
    geography: str
    source_title: str
    source_url: str


class DealResearchEngine:
    """Collects credible sources and extracts structured deal records."""

    CREDIBLE_DOMAINS = {
        "reuters.com",
        "bloomberg.com",
        "ft.com",
        "wsj.com",
        "businesswire.com",
        "cnbc.com",
        "pitchbook.com",
        "mergermarket.com",
        "privateequityinternational.com",
        "spglobal.com",
    }

    RSS_FEEDS = [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://www.businesswire.com/rss/home/?rss=G1QFDERJXkJeEFhW",
        "https://www.ft.com/rss/home",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    ]

    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    @staticmethod
    def _domain(url: str) -> str:
        return urlparse(url).netloc.lower().replace("www.", "")

    def _is_credible(self, url: str) -> bool:
        domain = self._domain(url)
        return any(domain.endswith(d) for d in self.CREDIBLE_DOMAINS)

    def _search_duckduckgo(self, query: str) -> list[dict[str, Any]]:
        focused = (
            f"{query} private equity acquisition EV/EBITDA EV/Revenue deal announcement "
            "last 12 months"
        )
        with DDGS() as ddgs:
            results = list(ddgs.text(focused, max_results=settings.max_search_results))
        normalized: list[dict[str, Any]] = []
        for result in results:
            href = result.get("href") or result.get("url")
            if not href or not self._is_credible(href):
                continue
            normalized.append(
                {
                    "title": result.get("title", "Untitled"),
                    "url": href,
                    "snippet": result.get("body", ""),
                    "source": self._domain(href),
                    "published": None,
                }
            )
        return normalized

    def _search_tavily(self, query: str) -> list[dict[str, Any]]:
        if not settings.tavily_api_key:
            return []
        headers = {
            "Authorization": f"Bearer {settings.tavily_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": f"{query} M&A private equity valuation multiple",
            "search_depth": "advanced",
            "max_results": 10,
            "include_raw_content": False,
            "topic": "news",
        }

        async def _fetch() -> list[dict[str, Any]]:
            timeout = aiohttp.ClientTimeout(total=settings.request_timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://api.tavily.com/search", headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return data.get("results", [])

        raw = asyncio.run(_fetch())
        normalized: list[dict[str, Any]] = []
        for item in raw:
            url = item.get("url")
            if not url or not self._is_credible(url):
                continue
            normalized.append(
                {
                    "title": item.get("title", "Untitled"),
                    "url": url,
                    "snippet": item.get("content", ""),
                    "source": self._domain(url),
                    "published": item.get("published_date"),
                }
            )
        return normalized

    def _collect_rss(self, query: str) -> list[dict[str, Any]]:
        keywords = [k.strip().lower() for k in re.split(r"\s+", query) if len(k.strip()) > 2]
        found: list[dict[str, Any]] = []
        for feed_url in self.RSS_FEEDS:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:35]:
                link = entry.get("link")
                if not link or not self._is_credible(link):
                    continue
                text_blob = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                if keywords and not any(k in text_blob for k in keywords[:5]):
                    continue
                found.append(
                    {
                        "title": entry.get("title", "Untitled"),
                        "url": link,
                        "snippet": re.sub("<[^>]+>", "", entry.get("summary", "")),
                        "source": self._domain(link),
                        "published": entry.get("published"),
                    }
                )
        return found

    async def _fetch_content(self, session: aiohttp.ClientSession, item: dict[str, Any]) -> SourceItem | None:
        url = item["url"]
        try:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status >= 400:
                    return None
                html = await resp.text(errors="ignore")
            extracted = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
            text = re.sub(r"\s+", " ", extracted).strip()[:8000]
            if len(text) < 280:
                return None
            return SourceItem(
                title=item["title"],
                url=url,
                outlet=item.get("source", "Unknown"),
                published=item.get("published"),
                snippet=item.get("snippet", "")[:420],
                content=text,
            )
        except Exception:
            return None

    async def collect_sources(self, query: str) -> list[SourceItem]:
        candidates = []
        candidates.extend(self._search_tavily(query))
        candidates.extend(self._search_duckduckgo(query))
        candidates.extend(self._collect_rss(query))

        dedup: dict[str, dict[str, Any]] = {c["url"]: c for c in candidates}
        timeout = aiohttp.ClientTimeout(total=settings.request_timeout_seconds)
        connector = aiohttp.TCPConnector(limit=12)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            tasks = [self._fetch_content(session, c) for c in dedup.values()]
            results = await asyncio.gather(*tasks)
        valid = [r for r in results if r]
        valid.sort(key=lambda x: (x.published or ""), reverse=True)
        return valid[: settings.max_deals + 4]

    def _parse_deals_from_source(self, query: str, source: SourceItem) -> list[DealRecord]:
        if not self.client:
            return []
        prompt = f"""
Extract up to 3 relevant mid-market deal records from the source below.

Query context: {query}
Source title: {source.title}
Source url: {source.url}
Source outlet: {source.outlet}
Published: {source.published}

Source content:
{source.content}

Return STRICT JSON as:
{{"deals": [
  {{"date":"", "target":"", "acquirer":"", "deal_size":"", "valuation_multiple":"", "strategic_rationale":"", "revenue":"", "buyer_type":"PE|Strategic|Growth Equity|Other", "sector":"", "geography":""}}
]}}

Rules:
- Only include actual announced/completed transactions.
- Deal size or valuation_multiple can be "Not disclosed" when absent.
- If multiple can be inferred, format like "~11.5x EV/EBITDA (inferred)".
- Keep strategic_rationale <= 24 words.
"""
        response = self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You extract M&A deal facts accurately."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []

        deals: list[DealRecord] = []
        for d in payload.get("deals", [])[:3]:
            target = (d.get("target") or "").strip()
            acquirer = (d.get("acquirer") or "").strip()
            if not target or not acquirer:
                continue
            deals.append(
                DealRecord(
                    date=d.get("date") or source.published or "Unknown",
                    target=target,
                    acquirer=acquirer,
                    deal_size=d.get("deal_size") or "Not disclosed",
                    valuation_multiple=d.get("valuation_multiple") or "Not disclosed",
                    strategic_rationale=d.get("strategic_rationale") or "Not stated",
                    revenue=d.get("revenue") or "Not disclosed",
                    buyer_type=d.get("buyer_type") or "Other",
                    sector=d.get("sector") or "Unspecified",
                    geography=d.get("geography") or "Unspecified",
                    source_title=source.title,
                    source_url=source.url,
                )
            )
        return deals

    def build_deal_universe(self, query: str) -> tuple[list[DealRecord], list[SourceItem]]:
        sources = asyncio.run(self.collect_sources(query))
        all_deals: list[DealRecord] = []
        for source in sources:
            all_deals.extend(self._parse_deals_from_source(query, source))

        # de-duplicate deals by target+acquirer
        dedup: dict[tuple[str, str], DealRecord] = {}
        for deal in all_deals:
            key = (deal.target.lower(), deal.acquirer.lower())
            if key not in dedup:
                dedup[key] = deal
        deals = list(dedup.values())[: settings.max_deals]
        return deals, sources


def deals_to_dict_rows(deals: list[DealRecord]) -> list[dict[str, str]]:
    return [asdict(d) for d in deals]
