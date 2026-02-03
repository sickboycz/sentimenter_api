# Endpoints (v1.0)

Minimal required endpoint behavior:

1) Cluster detail returns allocations:
   GET /v1/news/clusters/{cluster_id}
   response includes:
   - market_impacts[]
   - sector_impacts[]
   - ticker_impacts[] (top winners/losers and/or full)

2) Debug endpoint:
   GET /v1/debug/asset_targeting/{cluster_id}
   returns:
   - packet + hashes
   - cache status for A/B/C
   - channels
   - sector raw & normalized scores
   - candidate generation diagnostics
   - final allocations
   - invariant violations (if any)

