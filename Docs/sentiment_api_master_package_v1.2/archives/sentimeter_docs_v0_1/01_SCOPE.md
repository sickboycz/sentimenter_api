# 01_SCOPE.md
## Goal
Standalone system that:
- Scrapes current news + archive backfill
- Ingests SPY history (OHLCV) to correlate news → market reaction
- Produces sentiment index + impact-scored events
- Exposes API to query index, drivers, events, correlations, and RAG answers

## Non-goals (v0.1)
- No trading execution
- No paywall bypass (metadata-only for paywalled sources)
- No heavy fine-tuning (swap models via config)

## Outputs
- Sentiment Index ([-1,+1], uncertainty, impact_pressure)
- Event stream (clustered stories → structured events → impacted assets)
- Evidence links for every score
- Historical calibration priors + forward eval ledger
