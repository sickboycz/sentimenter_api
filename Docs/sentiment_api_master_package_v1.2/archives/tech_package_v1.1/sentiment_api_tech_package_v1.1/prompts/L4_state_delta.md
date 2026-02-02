# L4 Narrative State Delta — Contract v1.0

Purpose: maintain a small set of "state keys" that represent ongoing narratives
(trade tension rising, war escalation, inflation pressures easing, etc.).

## Input
- cluster_id (L3)
- previous state snapshot (for the same state_key) if available

## Output (JSON ONLY)

### JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "StateDeltaL4",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "cluster_id": { "type": "string" },
    "state_key": { "type": "string", "minLength": 3, "maxLength": 64 },

    "prev_state_en": { "type": ["string", "null"], "maxLength": 200 },
    "new_state_en": { "type": "string", "minLength": 1, "maxLength": 200 },

    "change_direction": {
      "type": "string",
      "enum": ["up", "down", "sideways", "unknown"]
    },

    "change_confidence": { "type": "number", "minimum": 0, "maximum": 1 },

    "supporting_clusters": {
      "type": "array",
      "maxItems": 10,
      "items": { "type": "string" }
    },

    "notes_en": { "type": "string", "maxLength": 300 }
  },
  "required": [
    "cluster_id",
    "state_key",
    "prev_state_en",
    "new_state_en",
    "change_direction",
    "change_confidence",
    "supporting_clusters",
    "notes_en"
  ]
}
```

## State key namespace (v1 defaults)
- `rates_us`, `rates_eu`, `inflation_us`, `inflation_global`, `growth_global`
- `liquidity_stress`, `banking_stress`
- `geopolitics_middle_east`, `geopolitics_ukraine`, `geopolitics_taiwan`
- `sanctions_russia`, `sanctions_iran`, `trade_us_cn`
- `energy_oil_supply`, `shipping_red_sea`, `nuclear_risk`

You can extend this list over time; it is a controlled vocabulary to avoid explosion.

