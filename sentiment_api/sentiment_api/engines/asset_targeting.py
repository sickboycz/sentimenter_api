"""M5.5 — Asset targeting engine (markets/sectors/tickers)."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sentiment_api.db.pool import acquire

logger = logging.getLogger("sentiment_api.engines.asset_targeting")

# Map RiskOn/RiskOff to Up/Down for asset direction
DIRECTION_MAP = {"RiskOn": "Up", "RiskOff": "Down", "Neutral": "Neutral", "Mixed": "Mixed", "Unknown": "Unknown"}


def _empty_bundle(as_of: datetime, scope: dict) -> dict:
    """Empty AssetImpactBundle."""
    return {
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "scope": scope,
        "most_affected_market": {
            "market_id": "SP500",
            "direction": "Neutral",
            "impact_score": 0,
            "confidence": 0,
            "horizon": "unknown",
            "channels": [],
            "rationale_bullets_en": [],
            "evidence_urls": [],
        },
        "markets": [
            {"market_id": "SP500", "direction": "Neutral", "impact_score": 0, "confidence": 0, "horizon": "unknown", "channels": [], "rationale_bullets_en": [], "evidence_urls": []},
            {"market_id": "NASDAQ_COMPOSITE", "direction": "Neutral", "impact_score": 0, "confidence": 0, "horizon": "unknown", "channels": [], "rationale_bullets_en": [], "evidence_urls": []},
        ],
        "sectors": [],
        "winners": [],
        "losers": [],
        "notes_en": "",
    }


async def get_asset_impacts_for_cluster(
    cluster_id: str,
    universes: list[str] | None = None,
    limit_tickers: int = 50,
    limit_sectors: int = 11,
) -> dict:
    """Get asset impacts for a single cluster (AC-M5.5)."""
    universes = universes or ["sp500", "nasdaq_composite"]
    scope = {"cluster_id": cluster_id, "universes": universes}
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT cluster_id, headline_en, impact, source_urls, last_seen
            FROM clusters WHERE cluster_id = $1
            """,
            cluster_id,
        )
    if not row:
        return _empty_bundle(datetime.now(timezone.utc), scope)
    imp = row["impact"] or {}
    direction = DIRECTION_MAP.get(imp.get("expected_direction", "Unknown"), "Unknown")
    score = float(imp.get("impact_score", 0) or 0)
    source_urls = list(row["source_urls"] or [])[:10]
    most_affected = {
        "market_id": "SP500" if score > 40 else "NASDAQ_COMPOSITE",
        "direction": direction,
        "impact_score": score,
        "confidence": float(imp.get("confidence", 0.5) or 0.5),
        "horizon": imp.get("horizon", "unknown") or "unknown",
        "channels": imp.get("reason_codes", [])[:5],
        "rationale_bullets_en": [row["headline_en"][:200]] if row["headline_en"] else [],
        "evidence_urls": source_urls,
    }
    markets = [
        {"market_id": "SP500", "direction": direction, "impact_score": score, "confidence": most_affected["confidence"], "horizon": most_affected["horizon"], "channels": most_affected["channels"], "rationale_bullets_en": most_affected["rationale_bullets_en"], "evidence_urls": source_urls},
        {"market_id": "NASDAQ_COMPOSITE", "direction": direction, "impact_score": score * 0.9, "confidence": most_affected["confidence"] * 0.95, "horizon": most_affected["horizon"], "channels": most_affected["channels"], "rationale_bullets_en": most_affected["rationale_bullets_en"], "evidence_urls": source_urls[:5]},
    ]
    sectors: list[dict] = []
    winners: list[dict] = []
    losers: list[dict] = []
    ticker_rows: list = []
    if score >= 20:
        try:
            async with acquire() as conn2:
                sector_rows = await conn2.fetch("SELECT sector_id, name_en FROM sectors ORDER BY sector_id LIMIT $1", limit_sectors)
                for s in sector_rows[:5]:
                    sectors.append({
                        "sector_id": s["sector_id"],
                        "sector_name_en": s["name_en"],
                        "direction": direction,
                        "impact_score": score * 0.7,
                        "confidence": most_affected["confidence"] * 0.8,
                        "horizon": most_affected["horizon"],
                        "channels": most_affected["channels"],
                        "rationale_bullets_en": most_affected["rationale_bullets_en"],
                    })
                ticker_rows = await conn2.fetch(
                    """
                    SELECT s.symbol, s.name, s.sector_id, sec.name_en as sector_name_en
                    FROM universe_memberships um
                    JOIN securities s ON s.symbol = um.symbol
                    LEFT JOIN sectors sec ON sec.sector_id = s.sector_id
                    WHERE um.universe_id = ANY($1)
                      AND (um.effective_to IS NULL OR um.effective_to >= current_date)
                    ORDER BY s.symbol
                    LIMIT $2
                    """,
                    universes,
                    limit_tickers,
                )
        except Exception as e:
            logger.warning("Asset targeting fetch failed: %s", e)
            ticker_rows = []
        for t in ticker_rows[:limit_tickers // 2]:
            tick = {
                "symbol": t["symbol"],
                "name": t["name"] or t["symbol"],
                "universe_memberships": universes,
                "sector_id": t["sector_id"] or "unknown",
                "sector_name_en": t["sector_name_en"] or "Unknown",
                "direction": direction,
                "impact_score": score * 0.5,
                "confidence": 0.4,
                "horizon": most_affected["horizon"],
                "channels": most_affected["channels"],
                "rationale_bullets_en": [row["headline_en"][:150]] if row["headline_en"] else [],
                "driver_clusters": [cluster_id],
                "evidence_urls": source_urls[:3],
                "historical_edge": [],
            }
            if direction == "Up":
                winners.append(tick)
            elif direction == "Down":
                losers.append(tick)
    as_of = datetime.now(timezone.utc)
    return {
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "scope": scope,
        "most_affected_market": most_affected,
        "markets": markets,
        "sectors": sectors,
        "winners": winners[:limit_tickers],
        "losers": losers[:limit_tickers],
        "notes_en": f"Cluster {cluster_id} asset targeting.",
    }


async def get_latest_asset_impacts(
    window: str = "6h",
    since: datetime | None = None,
    until: datetime | None = None,
    min_impact_level: str = "L2",
    universes: list[str] | None = None,
    limit_tickers: int = 50,
    limit_sectors: int = 11,
) -> dict:
    """Get aggregated asset impacts for latest qualifying clusters (AC-M5.5.6)."""
    universes = universes or ["sp500", "nasdaq_composite"]
    until = until or datetime.now(timezone.utc)
    window_sec = {"1h": 3600, "2h": 7200, "6h": 21600, "12h": 43200, "24h": 86400, "3d": 259200, "7d": 604800}.get(window, 21600)
    since = since or (until - timedelta(seconds=window_sec))
    level_order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
    min_level = level_order.get(min_impact_level, 2)
    scope = {"since": since.isoformat().replace("+00:00", "Z"), "until": until.isoformat().replace("+00:00", "Z"), "min_impact_level": min_impact_level, "universes": universes}
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT cluster_id FROM clusters
            WHERE last_seen >= $1 AND last_seen <= $2
              AND CASE (impact->>'impact_level')
                WHEN 'L0' THEN 0 WHEN 'L1' THEN 1 WHEN 'L2' THEN 2
                WHEN 'L3' THEN 3 WHEN 'L4' THEN 4 WHEN 'L5' THEN 5 ELSE 0 END >= $3
            ORDER BY (impact->>'impact_score')::float DESC
            LIMIT 20
            """,
            since,
            until,
            min_level,
        )
    if not rows:
        return _empty_bundle(until, scope)
    bundle = await get_asset_impacts_for_cluster(rows[0]["cluster_id"], universes, limit_tickers, limit_sectors)
    bundle["scope"] = scope
    bundle["as_of"] = until.isoformat().replace("+00:00", "Z")
    return bundle
