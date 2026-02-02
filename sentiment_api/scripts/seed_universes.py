#!/usr/bin/env python3
"""Seed sectors and universes from registry. Run after applying v1.1 migration."""

import asyncio
from datetime import date

from sentiment_api.config import get_settings
from sentiment_api.db.pool import init_pool, acquire
from sentiment_api.db.universe_repo import (
    seed_sectors,
    upsert_universe,
    upsert_security,
    upsert_universe_membership,
)

# Minimal S&P 500 sample (top 20 by weight) for demo - replace with full refresh in production
SP500_SAMPLE = [
    ("AAPL", "Apple Inc.", "information_technology"),
    ("MSFT", "Microsoft Corporation", "information_technology"),
    ("GOOGL", "Alphabet Inc.", "communication_services"),
    ("AMZN", "Amazon.com Inc.", "consumer_discretionary"),
    ("NVDA", "NVIDIA Corporation", "information_technology"),
    ("META", "Meta Platforms Inc.", "communication_services"),
    ("BRK.B", "Berkshire Hathaway Inc.", "financials"),
    ("JPM", "JPMorgan Chase & Co.", "financials"),
    ("V", "Visa Inc.", "financials"),
    ("XOM", "Exxon Mobil Corporation", "energy"),
    ("UNH", "UnitedHealth Group Inc.", "health_care"),
    ("JNJ", "Johnson & Johnson", "health_care"),
    ("PG", "Procter & Gamble Co.", "consumer_staples"),
    ("MA", "Mastercard Inc.", "financials"),
    ("HD", "Home Depot Inc.", "consumer_discretionary"),
    ("CVX", "Chevron Corporation", "energy"),
    ("ABBV", "AbbVie Inc.", "health_care"),
    ("MRK", "Merck & Co. Inc.", "health_care"),
    ("PEP", "PepsiCo Inc.", "consumer_staples"),
    ("KO", "Coca-Cola Co.", "consumer_staples"),
]


async def main():
    settings = get_settings()
    await init_pool(settings.database_url)
    async with acquire() as conn:
        await seed_sectors(conn)
        await upsert_universe(conn, "sp500", "S&P 500", "seed", "S&P 500 constituents")
        await upsert_universe(conn, "nasdaq_composite", "Nasdaq Composite", "seed", "Nasdaq Composite constituents")
        eff = date.today()
        for symbol, name, sector_id in SP500_SAMPLE:
            await upsert_security(conn, symbol, name, sector_id)
            await upsert_universe_membership(conn, "sp500", symbol, eff)
    print("Seeded sectors + sp500 sample (20 tickers)")


if __name__ == "__main__":
    asyncio.run(main())
