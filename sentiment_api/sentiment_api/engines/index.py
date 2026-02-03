"""M6 — Index engine (intraday + daily, Moodix-compatible)."""

import logging
from datetime import datetime, date, timedelta, timezone
from typing import Any

from sentiment_api.db.pool import acquire
from sentiment_api.db.repo import insert_sentiment_tick, upsert_sentiment_daily

logger = logging.getLogger("sentiment_api.engines.index")


def _date_trunc_precision(interval: str) -> str:
    """Map interval label to PostgreSQL date_trunc precision."""
    if interval in ("1m", "5m", "15m"):
        return "minute"
    if interval == "1h":
        return "hour"
    return "minute"


async def compute_intraday_from_clusters(interval: str = "5m") -> None:
    """Compute intraday index from recent clusters (AC-M6.1)."""
    precision = _date_trunc_precision(interval)
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                date_trunc($1::text, last_seen) as bucket,
                (impact->>'impact_score')::float as score,
                impact->>'expected_direction' as direction
            FROM clusters
            WHERE last_seen >= now() - interval '24 hours'
              AND (impact->>'impact_level') NOT IN ('L0')
            """,
            precision,
        )
    if not rows:
        return
    buckets: dict[datetime, list[tuple[float, str]]] = {}
    for r in rows:
        ts = r["bucket"]
        if ts:
            buckets.setdefault(ts, []).append((r["score"] or 0, r["direction"] or "Neutral"))
    direction_score = {"RiskOn": 0.5, "RiskOff": -0.5, "Neutral": 0, "Mixed": 0, "Unknown": 0}
    for ts, items in buckets.items():
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        vol = len(items)
        scores = [s for s, _ in items]
        avg_score = sum(scores) / len(scores) if scores else 0
        volatility = (max(scores) - min(scores)) / 100.0 if scores else 0
        dirs = [direction_score.get(d, 0) for _, d in items]
        index_val = sum(dirs) / len(dirs) if dirs else 0
        sentiment = "RiskOff" if index_val < -0.2 else ("RiskOn" if index_val > 0.2 else "Neutral")
        try:
            async with acquire() as conn:
                await insert_sentiment_tick(
                    conn, ts, interval, index_val, vol, volatility, sentiment, 0.6, []
                )
        except Exception as e:
            logger.warning("Insert sentiment tick failed: %s", e)


async def compute_daily_ohlc(d: date | None = None) -> None:
    """Compute daily OHLC from intraday (AC-M6.2, AC-M6.3)."""
    d = d or date.today()
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ts, index_value, news_volume, news_volatility, sentiment
            FROM sentiment_timeseries
            WHERE interval = '5m' AND ts::date = $1
            ORDER BY ts
            """,
            d,
        )
    if not rows:
        return
    values = [float(r["index_value"]) for r in rows]
    open_v = values[0]
    high = max(values)
    low = min(values)
    close = values[-1]
    moodix = close
    vol = sum(r["news_volume"] or 0 for r in rows)
    vol_s = sum(float(r["news_volatility"] or 0) for r in rows) / len(rows) if rows else 0
    async with acquire() as conn:
        ma5_rows = await conn.fetch(
            """
            SELECT close FROM sentiment_daily WHERE date <= $1 ORDER BY date DESC LIMIT 5
            """,
            d,
        )
        ma10_rows = await conn.fetch(
            """
            SELECT close FROM sentiment_daily WHERE date <= $1 ORDER BY date DESC LIMIT 10
            """,
            d,
        )
    ma5 = sum(r["close"] for r in ma5_rows) / len(ma5_rows) if ma5_rows else None
    ma10 = sum(r["close"] for r in ma10_rows) / len(ma10_rows) if ma10_rows else None
    wave = (ma5 - ma10) if (ma5 is not None and ma10 is not None) else None
    sent = rows[-1]["sentiment"] if rows else "Neutral"
    try:
        async with acquire() as conn:
            await upsert_sentiment_daily(
                conn, d, open_v, high, low, close, moodix, ma5, ma10, wave, sent, vol, vol_s
            )
    except Exception as e:
        logger.warning("Upsert daily failed: %s", e)
