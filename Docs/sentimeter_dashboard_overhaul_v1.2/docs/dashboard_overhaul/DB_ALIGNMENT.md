# DB Alignment (Dashboard Overhaul v1.2)

Frontend assumes these API capabilities exist (already specified in v1.x docs):
- GET /v1/health
- GET /v1/mood/now
- GET /v1/index/intraday
- GET /v1/news/clusters
- GET /v1/news/clusters/{clusterId}
- GET /v1/impact/markets
- GET /v1/impact/sectors
- GET /v1/impact/tickers
- GET /v1/topics/index
- GET /v1/sources
- Optional: GET /v1/stream/events (SSE)

If backend lacks any of these, implement minimal additive routes + Pydantic responses consistent with error envelope.
Do not introduce breaking changes. Update OpenAPI + tests for any added route.
