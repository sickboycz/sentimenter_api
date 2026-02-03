"""RSS/Atom feed collector. Fallback: scrape webpage when feed returns 403 or fails."""

import logging
from datetime import datetime, timezone
from typing import Iterator

import feedparser
import httpx

from sentiment_api.collectors.base import RawItem
from sentiment_api.collectors.http_client import fetch_with_retry
from sentiment_api.registry.models import Source

logger = logging.getLogger("sentiment_api.collectors.rss")


class RSSCollector:
    """Collect items from RSS or Atom feeds (feedparser handles both). On 403/failure, optionally scrape fallback_page_url."""

    def __init__(self, timeout_sec: int = 20):
        self.timeout = timeout_sec

    def fetch_feed(self, feed_url: str, *, respect_robots: bool = True) -> feedparser.FeedParserDict:
        resp = fetch_with_retry(feed_url, timeout=float(self.timeout), respect_robots=respect_robots)
        return feedparser.parse(resp.content, response_headers=dict(resp.headers))

    def collect(self, source: Source, feed_url: str, *, respect_robots: bool = True) -> Iterator[RawItem]:
        """Yield raw items from RSS/Atom feed. On failure, fall back to scraping fallback_page_url if set."""
        try:
            feed = self.fetch_feed(feed_url, respect_robots=respect_robots)
        except Exception as e:
            logger.warning("RSS/Atom fetch failed %s: %s", feed_url, e)
            fallback = getattr(source, "fallback_page_url", None) or (source.config or {}).get("fallback_page_url")
            if fallback:
                logger.info("RSS fallback: scraping %s for %s", fallback, source.source_id)
                from sentiment_api.collectors.scrape import ScrapeCollector
                scrape = ScrapeCollector(timeout_sec=self.timeout)
                yield from scrape.collect(source, fallback, respect_robots=respect_robots)
            return
        now = datetime.now(timezone.utc)
        for entry in feed.entries:
            link = entry.get("link") or ""
            if not link:
                continue
            published = None
            for key in ("published_parsed", "updated_parsed"):
                ts = entry.get(key)
                if ts:
                    try:
                        published = datetime(*ts[:6], tzinfo=timezone.utc)
                        break
                    except (TypeError, ValueError):
                        pass
            title = entry.get("title") or entry.get("link", "")[:200]
            content = ""
            for key in ("content", "summary", "description"):
                val = entry.get(key)
                if isinstance(val, str):
                    content = val
                    break
                if isinstance(val, list) and val:
                    first = val[0]
                    content = first.get("value", str(first)) if isinstance(first, dict) else str(first)
                    break
            yield RawItem(
                source_id=source.source_id,
                source_type="rss",
                url=link,
                published_at=published,
                fetched_at=now,
                title_raw=title[:2000] if title else "",
                content_raw=content[:50000] if content else "",
                metadata={"feed_url": feed_url},
            )
