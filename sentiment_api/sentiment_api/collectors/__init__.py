"""M1 — Collectors (RSS, API, GDELT, scrape)."""

from sentiment_api.collectors.base import RawItem
from sentiment_api.collectors.rss import RSSCollector
from sentiment_api.collectors.gdelt import GDELTCollector
from sentiment_api.collectors.scrape import ScrapeCollector

__all__ = ["RawItem", "RSSCollector", "GDELTCollector", "ScrapeCollector"]
