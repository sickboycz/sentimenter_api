"""Daemon: orchestration loop (poll sources, push to ingest queue)."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from sentiment_api.config import get_settings
from sentiment_api.db.pool import init_pool, close_pool, acquire
from sentiment_api.collectors.rss import RSSCollector
from sentiment_api.collectors.gdelt import GDELTCollector
from sentiment_api.collectors.scrape import ScrapeCollector
from sentiment_api.queue.client import get_queue, QUEUE_INGEST
from sentiment_api.registry import load_registry

logger = logging.getLogger("sentiment_api.daemon")


def _serialize_item(item) -> dict:
    """Serialize RawItem for queue."""
    return {
        "source_id": item.source_id,
        "source_type": item.source_type,
        "url": item.url,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "fetched_at": item.fetched_at.isoformat() if item.fetched_at else None,
        "title_raw": item.title_raw,
        "content_raw": item.content_raw,
        "content_html": item.content_html,
        "metadata": item.metadata,
    }


async def _record_run(pool, run_type: str, source_id: str, count: int) -> None:
    from sentiment_api.db.pool import acquire
    from sentiment_api.db.repo import insert_run, finish_run
    async with acquire() as conn:
        run_id = await insert_run(conn, run_type, source_id, {"items_pushed": count})
        await finish_run(conn, run_id, "ok")


async def poll_source(source, queue, rss: RSSCollector, gdelt: GDELTCollector, scrape: ScrapeCollector) -> int:
    """Poll one source, push items to ingest queue. Returns count pushed."""
    count = 0
    try:
        if source.type == "rss" and source.feed_url:
            for item in rss.collect(source, source.feed_url):
                await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                count += 1
        elif source.type == "gdelt" and source.base_url:
            for item in gdelt.collect(source, source.base_url, source.query_profiles):
                await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                count += 1
        elif source.type == "scrape" and source.page_url:
            for item in scrape.collect(source, source.page_url):
                await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                count += 1
    except Exception as e:
        logger.warning("Poll %s failed: %s", source.source_id, e)
    if count > 0:
        try:
            from sentiment_api.db.pool import get_pool
            p = get_pool()
            if p:
                await _record_run(p, "ingest", source.source_id, count)
        except Exception:
            pass
    return count


async def run_daemon() -> None:
    """Main daemon loop: poll enabled sources on interval."""
    settings = get_settings()
    await init_pool(settings.database_url)
    queue = await get_queue(settings.redis_url)
    reg = load_registry(settings.source_registry_path)
    sources = reg.get_enabled_sources()
    interval = reg.defaults.update_interval_sec or 300
    rss = RSSCollector(timeout_sec=20)
    gdelt = GDELTCollector(timeout_sec=20)
    scrape = ScrapeCollector(timeout_sec=20)
    logger.info("Daemon started, polling %d sources every %ds", len(sources), interval)
    while True:
        try:
            total = 0
            for src in sources:
                n = await poll_source(src, queue, rss, gdelt, scrape)
                total += n
                if n > 0:
                    logger.debug("Source %s: %d items", src.source_id, n)
            if total > 0:
                logger.info("Poll cycle: %d items queued", total)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("Daemon error: %s", e)
        await asyncio.sleep(interval)
    await close_pool()
