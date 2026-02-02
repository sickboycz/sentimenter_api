"""Repository for universes, sectors, securities."""

from datetime import date
from typing import Any

import asyncpg

from sentiment_api.db.pool import acquire

# GICS-like 11 sectors + unknown (AC-M0.5.4)
GICS_11 = [
    ("unknown", "Unknown"),
    ("health_care", "Health Care"),
    ("information_technology", "Information Technology"),
    ("financials", "Financials"),
    ("consumer_discretionary", "Consumer Discretionary"),
    ("communication_services", "Communication Services"),
    ("industrials", "Industrials"),
    ("consumer_staples", "Consumer Staples"),
    ("energy", "Energy"),
    ("utilities", "Utilities"),
    ("real_estate", "Real Estate"),
    ("materials", "Materials"),
]


async def seed_sectors(conn: asyncpg.Connection) -> None:
    """Ensure GICS-like 11 sectors exist."""
    for sector_id, name_en in GICS_11:
        await conn.execute(
            """
            INSERT INTO sectors (sector_id, name_en, taxonomy)
            VALUES ($1, $2, 'gics_like')
            ON CONFLICT (sector_id) DO UPDATE SET name_en = EXCLUDED.name_en
            """,
            sector_id,
            name_en,
        )


async def upsert_universe(conn: asyncpg.Connection, universe_id: str, name_en: str, source: str, description_en: str | None = None) -> None:
    """Upsert universe."""
    await conn.execute(
        """
        INSERT INTO universes (universe_id, name_en, description_en, source, last_refreshed_at)
        VALUES ($1, $2, $3, $4, now())
        ON CONFLICT (universe_id) DO UPDATE SET
            name_en = EXCLUDED.name_en,
            description_en = EXCLUDED.description_en,
            source = EXCLUDED.source,
            last_refreshed_at = now()
        """,
        universe_id,
        name_en,
        description_en,
        source,
    )


async def upsert_security(conn: asyncpg.Connection, symbol: str, name: str, sector_id: str | None = None, exchange: str | None = None) -> None:
    """Upsert security."""
    await conn.execute(
        """
        INSERT INTO securities (symbol, name, sector_id, exchange, updated_at)
        VALUES ($1, $2, $3, $4, now())
        ON CONFLICT (symbol) DO UPDATE SET
            name = EXCLUDED.name,
            sector_id = COALESCE(EXCLUDED.sector_id, securities.sector_id),
            exchange = COALESCE(EXCLUDED.exchange, securities.exchange),
            updated_at = now()
        """,
        symbol,
        name,
        sector_id or "unknown",
        exchange,
    )


async def upsert_universe_membership(conn: asyncpg.Connection, universe_id: str, symbol: str, effective_from: date, effective_to: date | None = None, weight: float | None = None) -> None:
    """Upsert universe membership (idempotent)."""
    await conn.execute(
        """
        INSERT INTO universe_memberships (universe_id, symbol, effective_from, effective_to, weight)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (universe_id, symbol, effective_from) DO UPDATE SET
            effective_to = EXCLUDED.effective_to,
            weight = COALESCE(EXCLUDED.weight, universe_memberships.weight)
        """,
        universe_id,
        symbol,
        effective_from,
        effective_to,
        weight,
    )


async def list_universes(conn: asyncpg.Connection) -> list[dict]:
    """List universes with constituent counts."""
    rows = await conn.fetch(
        """
        SELECT u.universe_id, u.name_en, u.description_en, u.source, u.last_refreshed_at,
               (SELECT count(DISTINCT symbol) FROM universe_memberships um
                WHERE um.universe_id = u.universe_id
                  AND (um.effective_to IS NULL OR um.effective_to >= current_date)
                  AND um.effective_from <= current_date) as constituent_count
        FROM universes u
        ORDER BY u.universe_id
        """
    )
    return [
        {
            "universe_id": r["universe_id"],
            "name_en": r["name_en"],
            "description_en": r["description_en"],
            "source": r["source"],
            "as_of": r["last_refreshed_at"].isoformat().replace("+00:00", "Z") if r["last_refreshed_at"] else None,
            "constituent_count": r["constituent_count"] or 0,
        }
        for r in rows
    ]


async def list_sectors(conn: asyncpg.Connection) -> list[dict]:
    """List sector taxonomy."""
    rows = await conn.fetch("SELECT sector_id, name_en, taxonomy FROM sectors ORDER BY sector_id")
    return [{"sector_id": r["sector_id"], "name_en": r["name_en"], "taxonomy": r["taxonomy"]} for r in rows]


async def list_universe_constituents(
    conn: asyncpg.Connection,
    universe_id: str,
    as_of: date | None = None,
    sector_id: str | None = None,
    q: str | None = None,
    limit: int = 100,
    cursor: str | None = None,
) -> tuple[list[dict], str | None]:
    """List constituents (paged). Returns (rows, next_cursor)."""
    as_of = as_of or date.today()
    offset = int(cursor) if cursor and str(cursor).isdigit() else 0
    rows = await conn.fetch(
        """
        SELECT s.symbol, s.name, s.exchange, s.sector_id, sec.name_en as sector_name_en
        FROM universe_memberships um
        JOIN securities s ON s.symbol = um.symbol
        LEFT JOIN sectors sec ON sec.sector_id = s.sector_id
        WHERE um.universe_id = $1 AND um.effective_from <= $2
          AND (um.effective_to IS NULL OR um.effective_to >= $2)
          AND ($3::text IS NULL OR s.sector_id = $3)
          AND ($4::text IS NULL OR s.symbol ILIKE $4 OR s.name ILIKE $4)
        ORDER BY s.symbol
        LIMIT $5 OFFSET $6
        """,
        universe_id,
        as_of,
        sector_id,
        f"%{q}%" if q else None,
        limit + 1,
        offset,
    )
    next_cursor = str(offset + limit) if len(rows) > limit else None
    rows = rows[:limit]
    return [
        {
            "symbol": r["symbol"],
            "name": r["name"],
            "exchange": r["exchange"],
            "sector_id": r["sector_id"] or "unknown",
            "sector_name_en": r["sector_name_en"] or "Unknown",
        }
        for r in rows
    ], next_cursor
