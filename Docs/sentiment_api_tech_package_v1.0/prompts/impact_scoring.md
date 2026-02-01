# Impact Scoring — Contract v1.0

Purpose: convert a story cluster (L3) into:
- impact_score (0..100)
- impact_level (L0..L5)
- expected_direction (RiskOn/RiskOff/Neutral/Mixed/Unknown)
- horizon (intraday/1d/3d/1w/1m/unknown)
- confidence (0..1)
- reason_codes[] (stable causal labels)
- risk_vector (internal dimensions)
- impacted_assets (SPY baseline + optional sectors/tickers)

## Input
- cluster_id + L3 summary + evidence
- current regime signals (optional): SPY realized vol, VIX proxy, market breadth, etc.
- recent narrative state (L4)

## Output (JSON ONLY)

### JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ImpactScoreV1",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "cluster_id": { "type": "string" },

    "impact_score": { "type": "number", "minimum": 0, "maximum": 100 },
    "impact_level": { "type": "string", "enum": ["L0","L1","L2","L3","L4","L5"] },

    "expected_direction": {
      "type": "string",
      "enum": ["RiskOn","RiskOff","Neutral","Mixed","Unknown"]
    },

    "horizon": {
      "type": "string",
      "enum": ["intraday","1d","3d","1w","1m","unknown"]
    },

    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },

    "reason_codes": {
      "type": "array",
      "maxItems": 20,
      "items": {
        "type": "string",
        "enum": [
          "RATE_SURPRISE",
          "GUIDANCE_SHIFT",
          "INFLATION_SURPRISE",
          "GROWTH_SHOCK",
          "FISCAL_SHOCK",
          "LIQUIDITY_STRESS",
          "BANKING_STRESS",
          "CREDIT_EVENT",
          "SANCTIONS_EXPANSION",
          "WAR_ESCALATION",
          "WAR_DEESCALATION",
          "ELECTION_RISK",
          "TRADE_ESCALATION",
          "TRADE_DEESCALATION",
          "ENERGY_SUPPLY_SHOCK",
          "SHIPPING_DISRUPTION",
          "NUCLEAR_RISK",
          "DISASTER_DISRUPTION",
          "OTHER"
        ]
      }
    },

    "risk_vector": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "risk_appetite": { "type": "number", "minimum": -1, "maximum": 1 },
        "volatility_pressure": { "type": "number", "minimum": 0, "maximum": 1 },
        "growth_outlook": { "type": "number", "minimum": -1, "maximum": 1 },
        "inflation_pressure": { "type": "number", "minimum": -1, "maximum": 1 },
        "rates_pressure": { "type": "number", "minimum": -1, "maximum": 1 },
        "liquidity_stress": { "type": "number", "minimum": 0, "maximum": 1 },
        "geopolitical_risk": { "type": "number", "minimum": 0, "maximum": 1 },
        "energy_supply_risk": { "type": "number", "minimum": 0, "maximum": 1 }
      },
      "required": [
        "risk_appetite",
        "volatility_pressure",
        "growth_outlook",
        "inflation_pressure",
        "rates_pressure",
        "liquidity_stress",
        "geopolitical_risk",
        "energy_supply_risk"
      ]
    },

    "impacted_assets": {
      "type": "array",
      "maxItems": 25,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "instrument": { "type": "string", "minLength": 1 },
          "instrument_type": { "type": "string", "enum": ["ticker","etf","future","fx","rate"] },
          "direction": { "type": "string", "enum": ["RiskOn","RiskOff","Neutral","Mixed","Unknown"] },
          "weight": { "type": "number", "minimum": 0, "maximum": 1 },
          "impact_score": { "type": "number", "minimum": 0, "maximum": 100 }
        },
        "required": ["instrument","instrument_type","direction","weight","impact_score"]
      }
    },

    "impact_explanation_en": { "type": "string", "minLength": 0, "maxLength": 900 }
  },
  "required": [
    "cluster_id",
    "impact_score",
    "impact_level",
    "expected_direction",
    "horizon",
    "confidence",
    "reason_codes",
    "risk_vector",
    "impacted_assets",
    "impact_explanation_en"
  ]
}
```

## Scoring guidance (deterministic skeleton)
Use this mental model:
- Severity: credibility × source_count × novelty × urgency × scope
- Sensitivity: volatility regime × event_type_priority × time_of_day liquidity
- Exposure: topic-to-sector mapping (SPY proxy)
- Confidence: contradictions, missing data, weak evidence

Do not output “LLM vibes”. Output structured logic.

