"""Optional LLM-based asset targeting (when OPENAI_API_KEY set)."""

import json
import logging
import os
from typing import Any

from sentiment_api.llm.client import call_chat

logger = logging.getLogger("sentiment_api.llm.asset_targeting")

ASSET_TARGETING_SYSTEM = """You are an asset impact analyst. Output JSON ONLY.
Convert the news cluster into:
- markets[]: both SP500 and NASDAQ_COMPOSITE with direction (Up/Down/Neutral), impact_score (0-100), confidence (0-1), horizon, channels[], rationale_bullets_en[], evidence_urls[].
- sectors[]: top impacted sectors (sector_id, sector_name_en, direction, impact_score, confidence, horizon, channels[], rationale_bullets_en[]).
- winners[] and losers[]: tickers from the candidate list with symbol, name, universe_memberships, sector_id, direction, impact_score, confidence, channels[], rationale_bullets_en[], driver_clusters[], evidence_urls[], historical_edge[].
Use Up/Down for price direction. Be evidence-first. Do not invent tickers."""


def try_llm_asset_targeting(
    cluster_id: str,
    headline: str,
    topics: list[str],
    impact_score: float,
    direction: str,
    source_urls: list[str],
    candidate_tickers: list[dict],
    candidate_sectors: list[dict],
) -> dict | None:
    """Call LLM for asset targeting. Returns parsed bundle or None on failure."""
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    direction_map = {"RiskOn": "Up", "RiskOff": "Down", "Neutral": "Neutral", "Mixed": "Mixed", "Unknown": "Unknown"}
    dir_asset = direction_map.get(direction, "Unknown")
    user = f"""Cluster: {cluster_id}
Headline: {headline}
Topics: {topics}
Impact score: {impact_score}, direction: {dir_asset}
Evidence URLs: {source_urls[:5]}

Candidate tickers (use only these): {json.dumps([t.get("symbol") for t in candidate_tickers[:80]])}
Sectors: {json.dumps([s.get("sector_id") for s in candidate_sectors])}

Return JSON matching AssetImpactBundle: as_of, scope, most_affected_market, markets, sectors, winners, losers, notes_en."""
    out = call_chat(ASSET_TARGETING_SYSTEM, user)
    if not out:
        return None
    # Extract JSON (handle markdown code blocks)
    raw = out.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.debug("LLM asset targeting JSON parse failed: %s", e)
        return None
