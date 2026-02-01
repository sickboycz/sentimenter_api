"""M8 — Research engine (event studies vs SPY/ES)."""

import logging
from datetime import date, datetime, timedelta
from typing import Any

from sentiment_api.db.pool import acquire

logger = logging.getLogger("sentiment_api.engines.research")


async def run_event_study(
    from_date: date,
    to_date: date,
    market: str = "SPY",
    windows: list[str] | None = None,
    min_impact_level: str | None = None,
    direction: str | None = None,
) -> dict[str, Any]:
    """Run event study: align events to market bars, compute returns per window (AC-M8.1)."""
    windows = windows or ["30m", "2h", "1d", "3d", "1w"]
    tf_map = {"30m": "5m", "2h": "5m", "1d": "1d", "3d": "1d", "1w": "1d"}
    results = []
    async with acquire() as conn:
        events = await conn.fetch(
            """
            SELECT e.event_id, e.event_ts, e.expected_direction, e.impact_level
            FROM events e
            WHERE e.event_ts::date >= $1 AND e.event_ts::date <= $2
              AND ($3::text IS NULL OR e.impact_level >= $3::impact_level)
              AND ($4::text IS NULL OR e.expected_direction = $4)
            ORDER BY e.event_ts
            """,
            from_date,
            to_date,
            min_impact_level,
            direction,
        )
        if not events:
            for w in windows:
                results.append({
                    "window": w,
                    "mean_return": 0.0,
                    "median_return": 0.0,
                    "mean_abs_return": 0.0,
                    "hit_rate": 0.0,
                    "sample_size": 0,
                })
            return {"windows": results, "market": market, "from": str(from_date), "to": str(to_date)}

        bar_tf = "1d" if market == "SPY" else "1h"
        for w in windows:
            returns = []
            for ev in events:
                ets = ev["event_ts"]
                if ets.tzinfo is None:
                    ets = ets.replace(tzinfo=datetime.now().astimezone().tzinfo)
                window_sec = {"30m": 1800, "2h": 7200, "1d": 86400, "3d": 259200, "1w": 604800}.get(w, 86400)
                end_ts = ets + timedelta(seconds=window_sec)
                bars = await conn.fetch(
                    """
                    SELECT open, close FROM market_bars
                    WHERE symbol = $1 AND tf = $2 AND ts >= $3 AND ts <= $4
                    ORDER BY ts
                    """,
                    market,
                    bar_tf,
                    ets,
                    end_ts,
                )
                if len(bars) >= 2:
                    ret = (float(bars[-1]["close"]) - float(bars[0]["open"])) / float(bars[0]["open"]) if bars[0]["open"] else 0
                    returns.append(ret)
            n = len(returns)
            if n == 0:
                results.append({"window": w, "mean_return": 0.0, "median_return": 0.0, "mean_abs_return": 0.0, "hit_rate": 0.0, "sample_size": 0})
            else:
                mean_ret = sum(returns) / n
                sorted_r = sorted(returns)
                median_ret = sorted_r[n // 2] if n else 0
                mean_abs = sum(abs(r) for r in returns) / n
                hits = sum(1 for i, r in enumerate(returns) if i < len(events) and (
                    (events[i]["expected_direction"] == "RiskOn" and r > 0) or
                    (events[i]["expected_direction"] == "RiskOff" and r < 0)
                ))
                hit_rate = hits / n if n else 0
                results.append({
                    "window": w,
                    "mean_return": round(mean_ret, 6),
                    "median_return": round(median_ret, 6),
                    "mean_abs_return": round(mean_abs, 6),
                    "hit_rate": round(hit_rate, 4),
                    "sample_size": n,
                })
    return {"windows": results, "market": market, "from": str(from_date), "to": str(to_date)}
