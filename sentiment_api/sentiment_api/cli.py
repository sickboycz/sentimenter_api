"""CLI entry points."""

import argparse
import asyncio
import logging
import sys


def main():
    parser = argparse.ArgumentParser(prog="sentiment_api")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("api", help="Run API server")
    sub.add_parser("daemon", help="Run daemon (poll sources)")
    sub.add_parser("worker", help="Run worker (process queue)")
    sub.add_parser("refresh-universes", help="Refresh universe constituents (idempotent)")
    backfill_p = sub.add_parser("backfill", help="Backfill by date range (AC-M1.4)")
    backfill_p.add_argument("--from", dest="from_date", required=True, help="From date YYYY-MM-DD")
    backfill_p.add_argument("--to", dest="to_date", required=True, help="To date YYYY-MM-DD")
    backfill_p.add_argument("--source-id", dest="source_id", help="Optional source_id to limit")
    retention_p = sub.add_parser("retention", help="Run retention (tombstone old articles, AC-M7.3)")
    retention_p.add_argument("--days", type=int, default=90, help="Tombstone articles older than N days")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.cmd == "api":
        from sentiment_api.api.main import run
        run()
    elif args.cmd == "daemon":
        from sentiment_api.ingest.daemon import run_daemon
        asyncio.run(run_daemon())
    elif args.cmd == "worker":
        from sentiment_api.ingest.worker import run_worker
        asyncio.run(run_worker())
    elif args.cmd == "refresh-universes":
        from sentiment_api.universe.refresh import refresh_universes
        msg = asyncio.run(refresh_universes())
        print(msg)
    elif args.cmd == "backfill":
        from datetime import date
        from sentiment_api.ingest.backfill import run_backfill
        fd = date.fromisoformat(args.from_date)
        td = date.fromisoformat(args.to_date)
        result = asyncio.run(run_backfill(fd, td, getattr(args, "source_id", None) or None))
        print(result)
    elif args.cmd == "retention":
        async def _retention():
            from sentiment_api.db.pool import init_pool, close_pool
            from sentiment_api.db.retention import retire_old_articles
            from sentiment_api.config import get_settings
            settings = get_settings()
            await init_pool(settings.database_url)
            n = await retire_old_articles(getattr(args, "days", 90))
            await close_pool()
            return n
        n = asyncio.run(_retention())
        print(f"Tombstoned {n} articles")


if __name__ == "__main__":
    main()
