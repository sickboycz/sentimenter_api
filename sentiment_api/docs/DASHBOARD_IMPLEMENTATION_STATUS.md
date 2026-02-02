# Dashboard Implementation Status v1.2

## Full implementation ✓

| Feature | Status | Notes |
|---------|--------|-------|
| Design tokens | ✓ | `frontend/styles/tokens.css` — CSS vars for glass, colors, radii |
| Glass shell | ✓ | `.glass` in globals.css using tokens |
| Status pills (API, Ingestion, Allocation, Research) | ✓ | Topbar; data from `GET /v1/status` |
| Timeframe switch (1h / 6h / 24h) | ✓ | Topbar; context `useTimeframe()` |
| Global search stub | ✓ | Topbar input; no command palette logic |
| Overview page | ✓ | `/` — mood + impacts |
| News Feed | ✓ | `/news` — clusters |
| Cluster Detail | ✓ | `/clusters/[clusterId]` |
| Markets | ✓ | `/markets` — impacts |
| Sectors | ✓ | `/sectors` — heatmap + drilldown (tickers by sector) |
| Tickers | ✓ | `/tickers` — winners/losers |
| Topics | ✓ | `/topics` — topic indices |
| Research | ✓ | `/research` — event study |
| Sources | ✓ | `/sources` — source registry |
| Ops | ✓ | `/ops` — health, logs, links |
| Settings | ✓ | `/settings` — API key (dedicated page) |
| Backend `/v1/status` | ✓ | Returns api, ingestion, allocation, research |
| Zod validation | ✓ | `lib/schemas.ts` + `api.ts` validateResponse |
| Volume permissions script | ✓ | `scripts/check-permissions.sh` |

## Partial implementation

| Feature | Status | Notes |
|---------|--------|------|
| Ingestion / Allocation pills | Partial | Derived from `runs` table (ingest, summarize). Shows `unknown` if no recent runs. |
| Timeframe wiring to API | Partial | Context exists; pages can pass `window` from `useTimeframe()`. Some pages use hardcoded `6h`. |
| Virtualization for large lists | Partial | TODO in news/tickers; guardrails (limit 50). |
| 429 / 503 handling | ✓ | api.ts: 429 retry with Retry-After; 503 throws ApiDegradedError. |

## Optional

| Feature | Status | Notes |
|---------|--------|------|
| Research pill | Optional | No run type for research; always `unknown`. |
| Command palette | Optional | Search is stub; full palette not implemented. |
| Screenshots in CI | Optional | E2E may fail in headless env; screenshots on failure. |
| Additional Zod contracts | Optional | Basic envelope validation; strict per-endpoint contracts not required. |

## Backend support

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /v1/health` | No | Core dependency checks |
| `GET /v1/status` | No | Dashboard pills (api, ingestion, allocation, research) |
| `GET /v1/mood/now` | Yes | Overview mood |
| `GET /v1/index/intraday` | Yes | Intraday index |
| `GET /v1/news/clusters` | Yes | News clusters |
| `GET /v1/news/clusters/{id}` | Yes | Cluster detail |
| `GET /v1/impacts/latest` | Yes | Markets, sectors, tickers |
| `GET /v1/impacts/clusters/{id}` | Yes | Cluster impacts |
| `GET /v1/topics/index` | Yes | Topic indices |
| `GET /v1/research/spy/event-study` | Yes | Event study |
| `GET /v1/sources` | Yes | Source registry |
| `GET /v1/admin/logs` | Yes | Ops logs |
