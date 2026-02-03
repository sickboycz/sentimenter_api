#!/usr/bin/env python3
"""Print universe/ticker/sector/industry counts from the DB. Optional: run refresh first.
Usage:
  python scripts/confirm_universe_counts.py              # counts only
  python scripts/confirm_universe_counts.py --refresh  # refresh then counts
Or inside Docker: docker compose exec api python scripts/confirm_universe_counts.py --refresh
"""
import asyncio
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from sentiment_api.config import get_settings
from sentiment_api.db.pool import init_pool, acquire
from sentiment_api.universe.refresh import refresh_universes


async def main() -> None:
    do_refresh = "--refresh" in sys.argv
    if do_refresh:
        print("Refreshing universes from registry CSVs...")
        msg = await refresh_universes()
        print(msg)

    settings = get_settings()
    await init_pool(settings.database_url)

    async with acquire() as conn:
        n_sec = await conn.fetchval("SELECT COUNT(*) FROM securities")
        n_sectors = await conn.fetchval("SELECT COUNT(*) FROM sectors")
        try:
            n_industries = await conn.fetchval("SELECT COUNT(*) FROM industries")
        except Exception:
            n_industries = None
        rows = await conn.fetch(
            """SELECT u.universe_id, u.name_en, COUNT(m.symbol) AS constituents
               FROM universes u
               LEFT JOIN universe_memberships m ON m.universe_id = u.universe_id
                 AND m.effective_from <= CURRENT_DATE
                 AND (m.effective_to IS NULL OR m.effective_to >= CURRENT_DATE)
               GROUP BY u.universe_id, u.name_en
               ORDER BY u.universe_id"""
        )

    print("\n--- Universe / ticker / sector / industry counts ---")
    print(f"securities (unique tickers): {n_sec}")
    print(f"sectors:                    {n_sectors}")
    print(f"industries:                 {n_industries if n_industries is not None else 'N/A (table missing)'}")
    print("universes (constituents today):")
    for r in rows:
        print(f"  {r['universe_id']}: {r['constituents']}  ({r['name_en']})")
    print("---")


if __name__ == "__main__":
    asyncio.run(main())
