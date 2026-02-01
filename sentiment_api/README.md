# sentiment_api (Sentimeter)

Global macro + political + geopolitical news impact intelligence. API-only integration for IBKR dashboard/bot.

## Quick Start

### Option A: Local (API only, no DB)

```bash
cd sentiment_api
uv run sentiment-api api
# or: uv run uvicorn sentiment_api.api.main:app --host 0.0.0.0 --port 8080
# Health: http://localhost:8080/v1/health
# Sources: curl -H "X-API-Key: 0123456789abcdef0123456789abcdef" http://localhost:8080/v1/sources
```

### Option B: Full stack (Postgres + Redis + API + Worker + Daemon)

```bash
cd sentiment_api
docker compose up -d postgres redis

# Init DB schema (requires psql + pgvector)
psql postgresql://sentiment:sentiment@localhost:5432/sentiment -f ../Docs/sentiment_api_tech_package_v1.0/db/schema.sql

# Run services (in separate terminals)
uv run sentiment-api api      # API on :8080
uv run sentiment-api worker   # Process ingest queue
uv run sentiment-api daemon   # Poll sources, push to queue
```

### Option C: API in Docker

```bash
cd sentiment_api
docker compose up -d
# API at http://localhost:8080
```

## API Key

All endpoints except `/v1/health` require an API key:
- Header: `X-API-Key: <your-key>` (min 16 chars)
- Query: `?api_key=<your-key>` (Moodix-compatible)

## Build Order (Master Spec)

1. M0 — Source Registry + validator ✓
2. M1 — Collectors + queue
3. M2 — Normalization + translation
4. M3 — Dedup + clustering
5. M4 — Summaries L1–L4
6. M7 — Embeddings + vector retrieval
7. M5 — Impact engine
8. M6 — Index engine
9. M9 — API ✓
10. M8 — Research engine
11. M10 — Ops/monitoring ✓

## Endpoints

- `GET /api/sp-sentiment` — Moodix-compatible daily series
- `GET /v1/mood/now` — Current mood snapshot
- `GET /v1/index/intraday` — Intraday index
- `GET /v1/news/clusters` — Story clusters
- `GET /v1/news/clusters/{cluster_id}` — Cluster drilldown
- `GET /v1/research/spy/event-study` — Event studies (stub)
- `GET /v1/sources` — Source registry
- `GET /v1/health` — Health check (no auth)
