"""Measure outcomes for expectations (forward eval ledger)."""

import logging
from datetime import datetime, timedelta

from sentiment_api.db.pool import acquire

logger = logging.getLogger("sentiment_api.engines.outcomes")

WINDOW_SEC = {"30m": 1800, "2h": 7200, "1d": 86400, "3d": 259200, "1w": 604800}
DIRECTION_SCORE = {"RiskOn": 1, "RiskOff": -1, "Neutral": 0, "Mixed": 0, "Unknown": 0}


async def measure_outcomes(market: str = "SPY") -> int:
    """Measure outcomes for expectations that lack them. Returns count updated."""
    updated = 0
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT e.expectation_id, e.event_id, e.expected_direction, e.windows, ev.event_ts
            FROM expectations e
            JOIN events ev ON ev.event_id = e.event_id
            WHERE NOT EXISTS (SELECT 1 FROM outcomes o WHERE o.expectation_id = e.expectation_id)
            LIMIT 100
            """
        )
    for row in rows:
        exp_id = str(row["expectation_id"])
        event_ts = row["event_ts"]
        if event_ts.tzinfo is None:
            event_ts = event_ts.replace(tzinfo=datetime.now().astimezone().tzinfo)
        windows = row["windows"] or ["30m", "2h", "1d", "3d", "1w"]
        for w in windows:
            if w not in WINDOW_SEC:
                continue
            end_ts = event_ts + timedelta(seconds=WINDOW_SEC[w])
            async with acquire() as conn:
                bars = await conn.fetch(
                    """
                    SELECT open, close FROM market_bars
                    WHERE symbol = $1 AND tf = '1d' AND ts >= $2 AND ts <= $3
                    ORDER BY ts
                    """,
                    market,
                    event_ts,
                    end_ts,
                )
            if len(bars) < 2:
                continue
            ret = (float(bars[-1]["close"]) - float(bars[0]["open"])) / float(bars[0]["open"]) if bars[0]["open"] else 0
            realized = "RiskOn" if ret > 0.001 else ("RiskOff" if ret < -0.001 else "Neutral")
            try:
                async with acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO outcomes (expectation_id, window, realized_return, realized_abs_return, realized_direction)
                        VALUES ($1, $2, $3, $4, $5::direction)
                        ON CONFLICT (expectation_id, window) DO NOTHING
                        """,
                        exp_id,
                        w,
                        ret,
                        abs(ret),
                        realized,
                    )
                updated += 1
            except Exception as e:
                logger.warning("Outcome insert failed: %s", e)
    return updated
