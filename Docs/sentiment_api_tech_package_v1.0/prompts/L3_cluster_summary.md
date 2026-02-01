# L3 Cluster Summary — Contract v1.0

## Input
- cluster_id
- list of articles (L2 outputs recommended)
- evidence passages (extracted quotes)
- previous cluster state (optional; for delta)

## Output (JSON ONLY)

### JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ClusterSummaryL3",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "cluster_id": { "type": "string" },

    "headline_en": { "type": "string", "minLength": 1, "maxLength": 200 },

    "summary_bullets_en": {
      "type": "array",
      "minItems": 2,
      "maxItems": 8,
      "items": { "type": "string", "minLength": 1, "maxLength": 240 }
    },

    "what_changed_en": { "type": "string", "minLength": 0, "maxLength": 400 },

    "why_it_matters_en": { "type": "string", "minLength": 0, "maxLength": 500 },

    "what_to_watch_en": { "type": "string", "minLength": 0, "maxLength": 500 },

    "topics": { "type": "array", "maxItems": 20, "items": { "type": "string" } },

    "regions": { "type": "array", "maxItems": 20, "items": { "type": "string" } },

    "channels": {
      "type": "array",
      "maxItems": 10,
      "items": {
        "type": "string",
        "enum": [
          "rates",
          "inflation",
          "growth",
          "liquidity",
          "credit",
          "energy_supply",
          "geopolitical_risk",
          "sanctions",
          "trade",
          "risk_aversion",
          "flows",
          "other"
        ]
      }
    },

    "evidence": {
      "type": "array",
      "minItems": 2,
      "maxItems": 12,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "url": { "type": "string", "format": "uri" },
          "quote_en": { "type": "string", "minLength": 1, "maxLength": 240 },
          "relevance_score": { "type": "number", "minimum": 0, "maximum": 1 }
        },
        "required": ["url", "quote_en", "relevance_score"]
      }
    },

    "uncertainty_flags": {
      "type": "array",
      "maxItems": 20,
      "items": { "type": "string", "minLength": 1 }
    }
  },
  "required": [
    "cluster_id",
    "headline_en",
    "summary_bullets_en",
    "what_changed_en",
    "why_it_matters_en",
    "what_to_watch_en",
    "topics",
    "regions",
    "channels",
    "evidence",
    "uncertainty_flags"
  ]
}
```

## Output rules
- Keep bullets factual, not interpretive.
- `why_it_matters_en` can be interpretive but must link to channels and avoid speculation.
- If sources disagree, surface the disagreement explicitly and lower confidence later in impact scoring.

