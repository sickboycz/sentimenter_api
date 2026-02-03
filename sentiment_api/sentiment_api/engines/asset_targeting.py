"""M5.5 — Asset targeting engine (markets/sectors/tickers). Ticker whitelist enforced."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sentiment_api.db.pool import acquire

logger = logging.getLogger("sentiment_api.engines.asset_targeting")


def _filter_to_whitelist(bundle: dict, valid_symbols: set[str]) -> dict:
    """Filter winners/losers to only tickers in ticker_universe (non-negotiable rule 5)."""
    winners = [w for w in bundle.get("winners", []) if w.get("symbol") in valid_symbols]
    losers = [l for l in bundle.get("losers", []) if l.get("symbol") in valid_symbols]
    bundle = dict(bundle)
    bundle["winners"] = winners
    bundle["losers"] = losers
    return bundle


async def _get_valid_symbols(conn, universes: list[str]) -> set[str]:
    """Return symbols in universe_memberships for given universes."""
    rows = await conn.fetch(
        """
        SELECT DISTINCT um.symbol
        FROM universe_memberships um
        WHERE um.universe_id = ANY($1)
          AND (um.effective_to IS NULL OR um.effective_to >= current_date)
        """,
        universes,
    )
    return {r["symbol"] for r in rows}

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
    universes = universes or ["sp500", "nasdaq100"]
    scope = {"cluster_id": cluster_id, "universes": universes}
    async with acquire() as conn:
        valid_symbols = await _get_valid_symbols(conn, universes)
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
    # Optional: try LLM-based targeting when API key set and not cost_effective (fallback to rule-based)
    from sentiment_api.config import get_settings
    if score >= 20 and not get_settings().cost_effective:
        try:
            from sentiment_api.llm.asset_targeting import try_llm_asset_targeting
            async with acquire() as conn2:
                sector_rows = await conn2.fetch("SELECT sector_id, name_en FROM sectors ORDER BY sector_id LIMIT $1", limit_sectors)
                ticker_rows = await conn2.fetch(
                    """SELECT s.symbol, s.name, s.sector_id, sec.name_en as sector_name_en
                    FROM universe_memberships um JOIN securities s ON s.symbol = um.symbol
                    LEFT JOIN sectors sec ON sec.sector_id = s.sector_id
                    WHERE um.universe_id = ANY($1) AND (um.effective_to IS NULL OR um.effective_to >= current_date)
                    ORDER BY s.symbol LIMIT $2""",
                    universes, limit_tickers,
                )
            sectors_data = [{"sector_id": r["sector_id"], "name_en": r["name_en"]} for r in sector_rows]
            tickers_data = [{"symbol": r["symbol"], "name": r["name"], "sector_id": r["sector_id"]} for r in ticker_rows]
            llm_bundle = try_llm_asset_targeting(
                cluster_id, row["headline_en"] or "", list(row.get("topics", []) or []),
                score, imp.get("expected_direction", "Unknown"), source_urls,
                tickers_data, sectors_data,
            )
            if llm_bundle and llm_bundle.get("markets") and llm_bundle.get("sectors"):
                llm_bundle["scope"] = scope
                llm_bundle["as_of"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                llm_bundle = _filter_to_whitelist(llm_bundle, valid_symbols)
                return llm_bundle
        except Exception as ex:
            logger.debug("LLM asset targeting skipped: %s", ex)
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
    bundle = {
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "scope": scope,
        "most_affected_market": most_affected,
        "markets": markets,
        "sectors": sectors,
        "winners": winners[:limit_tickers],
        "losers": losers[:limit_tickers],
        "notes_en": f"Cluster {cluster_id} asset targeting.",
    }
    return _filter_to_whitelist(bundle, valid_symbols)


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
    universes = universes or ["sp500", "nasdaq100"]
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


def _bundle_to_event_impacts(bundle: dict, cluster_id: str) -> list[dict]:  # noqa: ARG001
    """Convert AssetImpactBundle to event_impacts rows for audit persistence."""
    rows = []
    for m in bundle.get("markets", []):
        rows.append({
            "instrument": m.get("market_id"),
            "instrument_type": "market",
            "direction": m.get("direction", "Unknown"),
            "impact_score": m.get("impact_score", 0),
            "horizon": m.get("horizon", "unknown"),
            "confidence": m.get("confidence", 0),
            "details": {"cluster_id": cluster_id, "rationale_bullets_en": m.get("rationale_bullets_en", [])},
        })
    for s in bundle.get("sectors", []):
        rows.append({
            "instrument": f"sector:{s.get('sector_id', 'unknown')}",
            "instrument_type": "sector",
            "direction": s.get("direction", "Unknown"),
            "impact_score": s.get("impact_score", 0),
            "horizon": s.get("horizon", "unknown"),
            "confidence": s.get("confidence", 0),
            "details": {"cluster_id": cluster_id},
        })
    for t in bundle.get("winners", []) + bundle.get("losers", []):
        rows.append({
            "instrument": t.get("symbol"),
            "instrument_type": "ticker",
            "direction": t.get("direction", "Unknown"),
            "impact_score": t.get("impact_score", 0),
            "horizon": t.get("horizon", "unknown"),
            "confidence": t.get("confidence", 0),
            "details": {"cluster_id": cluster_id, "universe_memberships": t.get("universe_memberships", [])},
        })
    return rows


async def persist_asset_targeting_audit(cluster_id: str, bundle: dict) -> None:
    """Persist full scoring table for audit (AC-M5.5.5)."""
    try:
        async with acquire() as conn:
            as_of = bundle.get("as_of") or datetime.now(timezone.utc).isoformat()
            scope = bundle.get("scope", {})
            await conn.execute(
                """
                INSERT INTO cluster_asset_targeting_audit (cluster_id, as_of, scope, bundle)
                VALUES ($1, $2::timestamptz, $3, $4)
                """,
                cluster_id,
                as_of,
                json.dumps(scope),
                json.dumps(bundle),
            )
    except Exception as e:
        logger.debug("Asset targeting audit persist skipped: %s", e)
