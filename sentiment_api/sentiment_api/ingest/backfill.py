"""Backfill by date range (AC-M1.4)."""

import asyncio
import json
import logging
from datetime import date, datetime, timedelta

from sentiment_api.config import get_settings
from sentiment_api.db.pool import init_pool, close_pool, acquire
from sentiment_api.collectors.rss import RSSCollector
from sentiment_api.collectors.gdelt import GDELTCollector
from sentiment_api.collectors.scrape import ScrapeCollector
from sentiment_api.queue.client import get_queue, QUEUE_INGEST
from sentiment_api.registry import load_registry
from sentiment_api.db.repo import insert_run, finish_run

logger = logging.getLogger("sentiment_api.ingest.backfill")


def _serialize_item(item) -> dict:
    return {
        "source_id": item.source_id,
        "source_type": item.source_type,
        "url": item.url,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "fetched_at": item.fetched_at.isoformat() if item.fetched_at else None,
        "title_raw": item.title_raw,
        "content_raw": item.content_raw,
        "content_html": item.content_html,
        "metadata": {**(item.metadata or {}), "backfill": True},
    }


async def run_backfill(from_date: date, to_date: date, source_id: str | None = None) -> dict:
    """Backfill sources by date range. Returns stats."""
    settings = get_settings()
    await init_pool(settings.database_url)
    queue = await get_queue(settings.redis_url)
    reg = load_registry(settings.source_registry_path)
    sources = reg.get_enabled_sources()
    if source_id:
        sources = [s for s in sources if s.source_id == source_id]
        if not sources:
            await close_pool()
            return {"error": "Source not found", "pushed": 0}
    rss = RSSCollector(timeout_sec=20)
    gdelt = GDELTCollector(timeout_sec=20)
    scrape = ScrapeCollector(timeout_sec=20)
    total = 0
    run_id = None
    try:
        async with acquire() as conn:
            run_id = await insert_run(conn, "backfill", None, {"from": str(from_date), "to": str(to_date)})
    except Exception as ex:
        logger.debug("Backfill insert_run skipped: %s", ex)
    start_str = from_date.strftime("%Y-%m-%d")
    end_str = to_date.strftime("%Y-%m-%d")
    for src in sources:
        count = 0
        respect_robots = src.effective_respect_robots_txt(reg.defaults)
        try:
            if src.type == "gdelt" and src.base_url:
                for item in gdelt.collect(src, src.base_url, getattr(src, "query_profiles", None), start_date=start_str, end_date=end_str, respect_robots=respect_robots):
                    await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                    count += 1
            elif src.type == "rss" and src.feed_url:
                for item in rss.collect(src, src.feed_url, respect_robots=respect_robots):
                    pub = item.published_at
                    if pub and from_date <= pub.date() <= to_date:
                        await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                        count += 1
            elif src.type == "scrape" and src.page_url:
                for item in scrape.collect(src, src.page_url, respect_robots=respect_robots):
                    pub = item.published_at
                    if pub and from_date <= pub.date() <= to_date:
                        await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                        count += 1
                    elif not pub:
                        await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                        count += 1
            elif src.type == "api":
                fallback = getattr(src, "fallback_page_url", None) or (src.config or {}).get("fallback_page_url")
                if fallback:
                    for item in scrape.collect(src, fallback, respect_robots=respect_robots):
                        pub = item.published_at
                        if pub and from_date <= pub.date() <= to_date:
                            await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                            count += 1
                        elif not pub:
                            await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                            count += 1
        except Exception as e:
            logger.warning("Backfill %s failed: %s", src.source_id, e)
        total += count
    if run_id:
        try:
            async with acquire() as conn:
                await finish_run(conn, run_id, "ok", None)
        except Exception as ex:
            logger.debug("Backfill finish_run skipped: %s", ex)
    await close_pool()
    return {"pushed": total, "sources": len(sources), "from": start_str, "to": end_str}
