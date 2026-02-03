#!/usr/bin/env python3
"""Backfill summarize queue: push articles without L2 summary to QUEUE_SUMMARIZE.

Run from sentiment_api/: uv run python scripts/backfill_summarize.py [--limit N] [--dry-run]
Useful when: articles exist but summarize queue was never drained (e.g. before queue-order fix).

Env: DATABASE_URL, REDIS_URL (from .env or environment). Loads .env from project root when available.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Load .env from project root so DATABASE_URL, REDIS_URL are available
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
except ImportError:
    pass

# Add project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sentiment_api.config import get_settings
from sentiment_api.db.pool import init_pool, close_pool, acquire
from sentiment_api.queue.client import get_queue, QUEUE_SUMMARIZE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_summarize")


class _DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        from datetime import datetime, date
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        return super().default(o)


async def main(limit: int | None, dry_run: bool) -> int:
    settings = get_settings()
    await init_pool(settings.database_url)
    queue = await get_queue(settings.redis_url)

    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT a.article_id, a.source_id, a.url, a.canonical_url, a.published_at, a.fetched_at,
                   a.title_en, a.content_en, a.metadata
            FROM articles a
            WHERE NOT EXISTS (
                SELECT 1 FROM summaries s
                WHERE s.object_type = 'article' AND s.object_id = a.article_id AND s.level = 'L2'
            )
            ORDER BY a.fetched_at DESC NULLS LAST
            LIMIT $1
            """,
            limit or 10000,
        )

    if not rows:
        logger.info("No articles without L2 summary; nothing to backfill.")
        await close_pool()
        return 0

    logger.info("Found %d articles without L2 summary", len(rows))
    pushed = 0

    for r in rows:
        norm = {
            "source_id": r["source_id"],
            "url": r["url"],
            "canonical_url": r["canonical_url"],
            "title_en": r["title_en"] or "",
            "content_en": r["content_en"] or "",
            "published_at": r["published_at"].isoformat() if r["published_at"] else "",
            "fetched_at": r["fetched_at"].isoformat() if r["fetched_at"] else "",
            "metadata": r["metadata"] or {},
        }
        payload = {"article_id": r["article_id"], "source_id": r["source_id"], "norm": norm}
        if not dry_run:
            await queue.rpush(QUEUE_SUMMARIZE, json.dumps(payload, cls=_DateTimeEncoder))
        pushed += 1
        if pushed <= 5 or pushed % 50 == 0:
            logger.info("Queued %s (article %s)", pushed, r["article_id"])

    logger.info("Backfill summarize: %d jobs %s", pushed, "would be queued (dry-run)" if dry_run else "queued")
    await close_pool()
    return pushed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push articles without L2 summary to summarize queue")
    parser.add_argument("--limit", type=int, default=None, help="Max articles to queue (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Log only, do not push")
    args = parser.parse_args()
    exit_code = 0 if asyncio.run(main(args.limit, args.dry_run)) >= 0 else 1
    sys.exit(exit_code)
