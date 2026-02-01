"""M5 — Impact scoring (formula-based + optional LLM)."""

import logging
from typing import Any

logger = logging.getLogger("sentiment_api.llm.impact")

LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5"]
DIRECTIONS = ["RiskOn", "RiskOff", "Neutral", "Mixed", "Unknown"]


def _level_from_score(score: float) -> str:
    if score < 5:
        return "L0"
    if score < 20:
        return "L1"
    if score < 40:
        return "L2"
    if score < 60:
        return "L3"
    if score < 80:
        return "L4"
    return "L5"


def _direction_from_topics(topics: list[str], channels: list[str]) -> str:
    risk_off = {"sanctions", "conflict", "war", "inflation", "rates", "liquidity", "credit", "geopolitical_risk"}
    risk_on = {"growth", "trade_deescalation", "war_deescalation"}
    all_tags = set(p.lower() for p in (topics or []) + (channels or []))
    if any(t in all_tags for t in risk_off):
        return "RiskOff"
    if any(t in all_tags for t in risk_on):
        return "RiskOn"
    return "Neutral"


def _risk_vector_default(direction: str) -> dict:
    base = {
        "risk_appetite": 0.0,
        "volatility_pressure": 0.3,
        "growth_outlook": 0.0,
        "inflation_pressure": 0.0,
        "rates_pressure": 0.0,
        "liquidity_stress": 0.0,
        "geopolitical_risk": 0.0,
        "energy_supply_risk": 0.0,
    }
    if direction == "RiskOff":
        base["risk_appetite"] = -0.5
        base["volatility_pressure"] = 0.6
    elif direction == "RiskOn":
        base["risk_appetite"] = 0.4
    return base


def score_impact(
    cluster_id: str,
    l3: dict,
    source_count: int = 1,
    credibility: str = "reputable_media",
) -> dict:
    """Compute impact score from L3 summary (AC-M5.1)."""
    topics = l3.get("topics", []) or []
    channels = l3.get("channels", []) or []
    direction = _direction_from_topics(topics, channels)
    cred_mult = {"official": 1.2, "reputable_media": 1.0, "local_media": 0.8, "dataset": 0.9, "user_added": 0.7}.get(
        credibility, 1.0
    )
    severity = min(1.0, 0.3 + 0.2 * source_count) * cred_mult
    sensitivity = 0.7
    exposure = 0.8
    confidence = 0.6 + 0.1 * min(len(topics), 3)
    impact_score = min(100, severity * sensitivity * exposure * confidence * 80)
    impact_level = _level_from_score(impact_score)
    reason_codes = []
    if "rates" in channels or "inflation" in channels:
        reason_codes.append("RATE_SURPRISE" if "inflation" in str(channels).lower() else "GUIDANCE_SHIFT")
    if "geopolitical_risk" in channels or "conflict" in str(topics).lower():
        reason_codes.append("GEOPOLITICAL_RISK")
    if "sanctions" in channels:
        reason_codes.append("SANCTIONS_EXPANSION")
    if "energy_supply" in str(channels).lower():
        reason_codes.append("ENERGY_SUPPLY_SHOCK")
    if not reason_codes:
        reason_codes.append("OTHER")
    horizon = "1d" if impact_level in ("L3", "L4", "L5") else "intraday"
    return {
        "cluster_id": cluster_id,
        "impact_score": round(impact_score, 1),
        "impact_level": impact_level,
        "expected_direction": direction,
        "horizon": horizon,
        "confidence": round(min(1.0, confidence), 2),
        "reason_codes": reason_codes[:10],
        "risk_vector": _risk_vector_default(direction),
        "impacted_assets": [{"instrument": "SPY", "instrument_type": "etf", "direction": direction, "weight": 1.0, "impact_score": impact_score}],
        "impact_explanation_en": l3.get("why_it_matters_en", "")[:500] or "",
    }
