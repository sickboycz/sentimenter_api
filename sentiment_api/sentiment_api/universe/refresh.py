"""Universe constituents refresh (idempotent, AC-M0.5.2)."""

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

# Extended S&P 500 + Nasdaq sample (top ~50 by market cap)
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
    ("AVGO", "Broadcom Inc.", "information_technology"),
    ("COST", "Costco Wholesale Corp.", "consumer_staples"),
    ("WMT", "Walmart Inc.", "consumer_staples"),
    ("LLY", "Eli Lilly and Co.", "health_care"),
    ("ADBE", "Adobe Inc.", "information_technology"),
    ("CRM", "Salesforce Inc.", "information_technology"),
    ("ORCL", "Oracle Corp.", "information_technology"),
    ("AMD", "Advanced Micro Devices", "information_technology"),
    ("INTC", "Intel Corp.", "information_technology"),
    ("TSLA", "Tesla Inc.", "consumer_discretionary"),
]
NASDAQ_EXTRA = [
    ("PYPL", "PayPal Holdings", "financials"),
    ("ZM", "Zoom Video Communications", "information_technology"),
]


async def refresh_universes() -> str:
    """Refresh sectors and universe constituents. Returns status message."""
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
        for symbol, name, sector_id in NASDAQ_EXTRA:
            await upsert_security(conn, symbol, name, sector_id)
            await upsert_universe_membership(conn, "nasdaq_composite", symbol, eff)
    return f"Refreshed sectors + sp500 ({len(SP500_SAMPLE)}) + nasdaq_composite ({len(NASDAQ_EXTRA)} extra)"


def run_refresh() -> None:
    """Synchronous entry point for CLI."""
    msg = asyncio.run(refresh_universes())
    print(msg)
