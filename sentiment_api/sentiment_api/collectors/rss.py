"""RSS feed collector."""

import logging
from datetime import datetime, timezone
from typing import Iterator

import feedparser
import httpx

from sentiment_api.collectors.base import RawItem
from sentiment_api.registry.models import Source

logger = logging.getLogger("sentiment_api.collectors.rss")


class RSSCollector:
    """Collect items from RSS feeds."""

    def __init__(self, timeout_sec: int = 20):
        self.timeout = timeout_sec

    def fetch_feed(self, feed_url: str) -> feedparser.FeedParserDict:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            resp = client.get(feed_url)
            resp.raise_for_status()
            return feedparser.parse(resp.content, response_headers=dict(resp.headers))

    def collect(self, source: Source, feed_url: str) -> Iterator[RawItem]:
        """Yield raw items from RSS feed."""
        try:
            feed = self.fetch_feed(feed_url)
        except Exception as e:
            logger.warning("RSS fetch failed %s: %s", feed_url, e)
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
                    content = val[0].get("value", "")
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
