"""Web page scraper collector."""

import logging
import re
from datetime import datetime, timezone
from typing import Iterator
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura

from sentiment_api.collectors.base import RawItem
from sentiment_api.collectors.http_client import fetch_with_retry
from sentiment_api.registry.models import Source

logger = logging.getLogger("sentiment_api.collectors.scrape")


class ScrapeCollector:
    """Scrape newsroom/list pages for article links."""

    def __init__(self, timeout_sec: int = 20):
        self.timeout = timeout_sec

    def _fetch(self, url: str) -> tuple[str, str]:
        resp = fetch_with_retry(url, timeout=float(self.timeout))
        html = resp.text
        text = trafilatura.extract(html) or ""
        return html, text

    def _extract_links(self, html: str, base_url: str) -> list[tuple[str, str]]:
        """Extract article-like links from page."""
        links = re.findall(r'href=["\']([^"\']+)["\']', html, re.I)
        base = urlparse(base_url)
        seen = set()
        results = []
        for href in links:
            href = href.strip().split("#")[0].split("?")[0]
            if not href or href.startswith(("#", "mailto:", "javascript:")):
                continue
            full = urljoin(base_url, href)
            p = urlparse(full)
            if p.netloc != base.netloc:
                continue
            path = p.path.rstrip("/") or "/"
            if path in seen:
                continue
            seen.add(path)
            if any(x in path.lower() for x in ["/news/", "/press/", "/article/", "/release/", ".htm", ".html", "/20"]):
                results.append((full, path))
        return results[:50]

    def collect(self, source: Source, page_url: str) -> Iterator[RawItem]:
        """Yield raw items from scraped page (one item per discovered article link)."""
        try:
            html, text = self._fetch(page_url)
        except Exception as e:
            logger.warning("Scrape fetch failed %s: %s", page_url, e)
            return
        now = datetime.now(timezone.utc)
        links = self._extract_links(html, page_url)
        if not links:
            yield RawItem(
                source_id=source.source_id,
                source_type="scrape",
                url=page_url,
                published_at=now,
                fetched_at=now,
                title_raw=text[:200] if text else page_url,
                content_raw=text[:50000] if text else "",
                metadata={"page_url": page_url},
            )
        else:
            for full_url, _ in links:
                yield RawItem(
                    source_id=source.source_id,
                    source_type="scrape",
                    url=full_url,
                    published_at=now,
                    fetched_at=now,
                    title_raw="",
                    content_raw="",
                    metadata={"page_url": page_url, "needs_fetch": True},
                )
