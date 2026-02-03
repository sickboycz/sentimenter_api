# Example Packets & Outputs (v1.0)

## Example cluster packet (shortened)
```json
{
  "cluster_id": "clu_demo_001",
  "cluster_version": 1,
  "headline_en": "Fed signals rate hike pause",
  "summary_bullets_en": ["Policy language shifts", "Rates fall", "Tech rallies"],
  "topics": ["rates","macro"],
  "regions": ["US"],
  "impact": {
    "impact_score": 78,
    "impact_level": "L4",
    "expected_direction": "RiskOn",
    "confidence": 0.66
  },
  "evidence": [
    {"id": 1, "url": "https://example.com/a", "text_en": "Officials emphasized data dependence..."}
  ],
  "direct_mentions": [{"symbol":"NVDA","match_quality":0.9,"evidence_ids":[1]}],
  "numeric_facts": [{"key":"rate_change_bps","value":-10}]
}
```

## Example Call A output (channels)
```json
{
  "channels": [
    {"name":"rates","sign":-1,"strength":0.7,"why_refs":[1],"short_why_en":"Rates expectations fall"},
    {"name":"risk_appetite","sign":1,"strength":0.6,"why_refs":[1],"short_why_en":"Risk appetite improves"}
  ],
  "primary_horizon":"intraday",
  "confidence":0.68,
  "rationale_bullets_en":["Policy pause shifts rate path","Risk appetite improves"]
}
```

## Example Call C output (allowlist picks)
```json
{
  "winners":[{"symbol":"NVDA","strength":0.7,"why_refs":[1],"short_why_en":"Growth bid on lower rates"}],
  "losers":[{"symbol":"DXY","strength":0.4,"why_refs":[1],"short_why_en":"Safe-haven demand fades"}]
}
```

