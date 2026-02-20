"""Automated web research engine for pulling recent, credible finance coverage."""
from __future__ import annotations

import asyncio
import datetime as dt
from dataclasses import dataclass
from typing import Iterable

import aiohttp
import feedparser
import trafilatura
from duckduckgo_search import DDGS


@dataclass
class SourceItem:
    """Represents one curated research source."""

    title: str
    url: str
    source: str
    published: str | None
    snippet: str
    extracted_text: str


class ResearchEngine:
    """Fetches high-quality sources and extracts useful text context asynchronously."""

    CREDIBLE_DOMAINS = {
        "reuters.com",
        "bloomberg.com",
        "ft.com",
        "wsj.com",
        "cnbc.com",
        "forbes.com",
        "economist.com",
        "yahoo.com",
        "marketwatch.com",
        "techcrunch.com",
        "crunchbase.com",
        "pitchbook.com",
        "mckinsey.com",
        "worldbank.org",
        "imf.org",
        "oecd.org",
        "sec.gov",
    }

    RSS_FEEDS = [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.feedburner.com/TechCrunch",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.ft.com/rss/home",
    ]

    def __init__(self, max_sources: int = 8, timeout_seconds: int = 8) -> None:
        self.max_sources = max_sources
        self.timeout_seconds = timeout_seconds

    def _is_credible(self, url: str) -> bool:
        return any(domain in url for domain in self.CREDIBLE_DOMAINS)

    def _web_search(self, query: str) -> list[dict]:
        focused_query = f"{query} finance markets deals funding valuation"
        with DDGS() as ddgs:
            results = list(ddgs.text(focused_query, max_results=20))
        return [r for r in results if self._is_credible(r.get("href", ""))]

    def _rss_search(self, query: str) -> list[dict]:
        query_words = {word.lower() for word in query.split() if len(word) > 2}
        items: list[dict] = []
        for feed_url in self.RSS_FEEDS:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:
                text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                if query_words and not any(word in text for word in query_words):
                    continue
                link = entry.get("link", "")
                if not self._is_credible(link):
                    continue
                items.append(
                    {
                        "title": entry.get("title", "Untitled"),
                        "href": link,
                        "body": entry.get("summary", ""),
                        "source": feed.feed.get("title", "RSS"),
                        "published": entry.get("published", None),
                    }
                )
        return items

    async def _fetch_extract(self, session: aiohttp.ClientSession, candidate: dict) -> SourceItem | None:
        url = candidate.get("href") or candidate.get("url")
        if not url:
            return None

        try:
            async with session.get(url, timeout=self.timeout_seconds, allow_redirects=True) as resp:
                if resp.status >= 400:
                    return None
                html = await resp.text(errors="ignore")
        except Exception:
            return None

        extracted = trafilatura.extract(html, include_comments=False, include_tables=True)
        extracted = (extracted or "").strip()
        if len(extracted) < 250:
            return None

        snippet = candidate.get("body") or extracted[:450]
        return SourceItem(
            title=candidate.get("title", "Untitled"),
            url=url,
            source=candidate.get("source", "Web"),
            published=candidate.get("published"),
            snippet=snippet,
            extracted_text=extracted[:2500],
        )

    async def _extract_all(self, candidates: Iterable[dict]) -> list[SourceItem]:
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds + 3)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [self._fetch_extract(session, c) for c in candidates]
            raw_results = await asyncio.gather(*tasks)
        return [item for item in raw_results if item is not None]

    async def research(self, query: str) -> list[SourceItem]:
        web_candidates = self._web_search(query)
        rss_candidates = self._rss_search(query)

        deduped: dict[str, dict] = {}
        for candidate in [*web_candidates, *rss_candidates]:
            link = candidate.get("href")
            if not link:
                continue
            deduped.setdefault(link, candidate)

        candidates = list(deduped.values())[: self.max_sources * 2]
        extracted = await self._extract_all(candidates)

        # Sort with simple recency preference when dates exist.
        def parse_date(item: SourceItem) -> dt.datetime:
            if not item.published:
                return dt.datetime(1970, 1, 1)
            for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z"):
                try:
                    return dt.datetime.strptime(item.published, fmt)
                except Exception:
                    continue
            return dt.datetime(1970, 1, 1)

        extracted.sort(key=parse_date, reverse=True)
        return extracted[: self.max_sources]
