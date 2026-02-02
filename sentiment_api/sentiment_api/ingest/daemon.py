"""Daemon: orchestration loop (poll sources, push to ingest queue)."""

import asyncio
import signal
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
from sentiment_api.collectors.circuit_breaker import is_open, record_success, record_failure
from sentiment_api.metrics import ingestion_errors_total, ingestion_lag_seconds, fetch_duration_seconds

logger = logging.getLogger("sentiment_api.daemon")

try:
    from sentiment_api.logging_file import add_file_handler
    add_file_handler("daemon")
except Exception:
    pass


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


async def _record_run(pool, run_type: str, source_id: str | None, status: str, stats: dict | None = None, error: dict | None = None) -> None:
    from sentiment_api.db.repo import insert_run, finish_run
    try:
        async with acquire() as conn:
            run_id = await insert_run(conn, run_type, source_id, stats or {})
            await finish_run(conn, run_id, status, error)
    except Exception as ex:
        logger.debug("Record run failed: %s", ex)


async def poll_source(source, queue, rss: RSSCollector, gdelt: GDELTCollector, scrape: ScrapeCollector, defaults) -> int:
    """Poll one source, push items to ingest queue. Returns count pushed."""
    import time
    if is_open(source.source_id):
        logger.debug("Circuit open for %s, skipping", source.source_id)
        return 0
    count = 0
    t0 = time.perf_counter()
    respect_robots = source.effective_respect_robots_txt(defaults)
    try:
        if source.type == "rss" and source.feed_url:
            for item in rss.collect(source, source.feed_url, respect_robots=respect_robots):
                await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                count += 1
        elif source.type == "gdelt" and source.base_url:
            for item in gdelt.collect(source, source.base_url, source.query_profiles, respect_robots=respect_robots):
                await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                count += 1
        elif source.type == "scrape" and source.page_url:
            for item in scrape.collect(source, source.page_url, respect_robots=respect_robots):
                await queue.rpush(QUEUE_INGEST, json.dumps(_serialize_item(item)))
                count += 1
    except Exception as e:
        record_failure(source.source_id)
        ingestion_errors_total(source.source_id)
        logger.warning("Poll %s failed: %s", source.source_id, e)
        try:
            from sentiment_api.db.pool import get_pool
            p = get_pool()
            if p:
                await _record_run(p, "ingest", source.source_id, "fail", {"items_pushed": 0}, {"message": str(e), "source_id": source.source_id})
        except Exception:
            pass
    finally:
        fetch_duration_seconds(source.source_id, time.perf_counter() - t0)
    if count > 0:
        record_success(source.source_id)
        ingestion_lag_seconds(source.source_id, None)  # record success
        try:
            from sentiment_api.db.pool import get_pool
            p = get_pool()
            if p:
                await _record_run(p, "ingest", source.source_id, "ok", {"items_pushed": count})
        except Exception:
            pass
    return count


_REGISTRY_RELOAD_INTERVAL = 10  # Reload registry every N poll cycles (AC-M0 hot reload)


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
    cycle = 0
    reload_requested = False

    def _sighup(_sig, _frame):
        nonlocal reload_requested
        reload_requested = True
        logger.info("SIGHUP received, registry reload scheduled")

    try:
        signal.signal(signal.SIGHUP, _sighup)
    except (AttributeError, ValueError):
        pass  # Windows / no SIGHUP

    while True:
        try:
            cycle += 1
            if reload_requested or cycle % _REGISTRY_RELOAD_INTERVAL == 0:
                reload_requested = False
                try:
                    reg = load_registry(settings.source_registry_path)
                    sources = reg.get_enabled_sources()
                    interval = reg.defaults.update_interval_sec or interval
                    logger.info("Registry reloaded: %d sources", len(sources))
                except Exception as ex:
                    logger.warning("Registry reload failed, using cached: %s", ex)
            total = 0
            for src in sources:
                n = await poll_source(src, queue, rss, gdelt, scrape, reg.defaults)
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
