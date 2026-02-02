"""GDELT DOC 2.0 API collector."""

import logging
from datetime import datetime, timezone
from typing import Iterator

import httpx

from sentiment_api.collectors.base import RawItem
from sentiment_api.collectors.http_client import fetch_with_retry
from sentiment_api.registry.models import Source, QueryProfile

logger = logging.getLogger("sentiment_api.collectors.gdelt")


class GDELTCollector:
    """Collect from GDELT DOC 2.0 API."""

    def __init__(self, timeout_sec: int = 20):
        self.timeout = timeout_sec

    def _query(self, base_url: str, query: str, mode: str = "artlist", max_records: int = 250) -> list[dict]:
        params = {"query": query, "mode": mode, "maxrecords": max_records, "format": "json"}
        resp = fetch_with_retry(base_url, params=params, timeout=float(self.timeout))
        data = resp.json()
        articles = data.get("articles", []) if isinstance(data, dict) else []
        return articles if isinstance(articles, list) else []

    def collect(self, source: Source, base_url: str, query_profiles: list[QueryProfile] | None = None) -> Iterator[RawItem]:
        """Yield raw items from GDELT API."""
        profiles = query_profiles or []
        if not profiles:
            profiles = [QueryProfile(profile_id="default", query="economy OR inflation OR politics")]
        seen_urls: set[str] = set()
        now = datetime.now(timezone.utc)
        for profile in profiles:
            try:
                articles = self._query(base_url, profile.query)
            except Exception as e:
                logger.warning("GDELT query failed %s: %s", profile.profile_id, e)
                continue
            for art in articles:
                url = art.get("url") or art.get("seendate", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                title = art.get("title") or art.get("snippet", "")[:200] or ""
                try:
                    ts = art.get("seendate") or art.get("socialimage")
                    published = None
                    if isinstance(ts, str) and len(ts) >= 8:
                        published = datetime.strptime(ts[:10], "%Y%m%d").replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    published = None
                yield RawItem(
                    source_id=source.source_id,
                    source_type="gdelt",
                    url=url,
                    published_at=published,
                    fetched_at=now,
                    title_raw=title[:2000],
                    content_raw=art.get("snippet", "")[:50000],
                    metadata={"query_profile": profile.profile_id},
                )
