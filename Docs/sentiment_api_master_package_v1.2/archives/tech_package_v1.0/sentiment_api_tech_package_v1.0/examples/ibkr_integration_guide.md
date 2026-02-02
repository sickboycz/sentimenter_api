# IBKR Dashboard/Bot Integration Guide (API-only) — v1.0

Goal: keep the IBKR bot *light and deterministic*.
No local LLM. The bot only:
- polls sentiment_api endpoints,
- filters by impact and regime,
- displays drivers / drill-down,
- optionally logs decisions.

## Recommended polling pattern
### 1) Intraday regime + volatility (fast, frequent)
- `GET /v1/mood/now` every 30–60 seconds during market hours.

Use:
- `sentiment` (RiskOn/RiskOff/Neutral) to switch your TA strategy mode
- `news_volatility_intraday` to dampen position sizing when news impact spikes
- `drivers[]` to show the top clusters behind moves

### 2) Actionable clusters (medium frequency)
- `GET /v1/news/clusters?since=<last_poll>&min_impact_level=L2`
  - every 60–120 seconds.

Rules of thumb:
- ignore L0–L1 by default
- treat L3+ as “market-moving”: display prominently and log
- for each cluster, if `expected_direction` conflicts with your TA direction, reduce risk or wait

### 3) Drill-down on demand (user click)
- `GET /v1/news/clusters/{cluster_id}?include_articles=true&include_evidence=true&include_analogs=true`

### 4) Daily overlay / historical view
- `GET /api/sp-sentiment?from=...&to=...`
  - once per day for chart overlays

## Suggested IBKR-side fields to store
- last_seen cluster_id set (dedupe notifications)
- last mood snapshot
- your internal “TA regime” vs sentiment_api regime divergence flag

## Divergence signals (high value)
- Moodix RiskOff but sentiment_api neutral → “news underreacted?” watch for delayed repricing
- sentiment_api L4/L5 cluster but TA says strong trend → reduce leverage, widen stops

## Fail-safe behavior
If sentiment_api is down:
- fall back to TA only
- set risk limits tighter (because you lose news risk visibility)

