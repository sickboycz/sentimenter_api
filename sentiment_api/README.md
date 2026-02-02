# sentiment_api (Sentimeter)

Global macro + political + geopolitical news impact intelligence. API-only integration for IBKR dashboard/bot.

## Quick Start

### Option A: Minimal (health only, no DB)

```bash
cd sentiment_api
uv run sentiment-api api
# Health (no auth): http://localhost:8080/v1/health
# Other endpoints require DB + API key
```

### Option B: Full stack (Postgres + Redis + API + Worker + Daemon)

```bash
cd sentiment_api
docker compose up -d postgres redis

# Init DB schema (requires psql + pgvector)
# v1.1: full schema
psql postgresql://sentiment:sentiment@localhost:5432/sentiment -f ../Docs/sentiment_api_tech_package_v1.1/db/schema.sql
# Or if upgrading from v1.0: psql ... -f migrations/v1.1_add_universes.sql
# Seed sectors + sample universes: uv run python scripts/seed_universes.py

# Create API key (required for protected endpoints)
uv run python scripts/create_api_key.py
# Use the printed key as X-API-Key

# Run services (in separate terminals)
uv run sentiment-api api      # API on :8080
uv run sentiment-api worker   # Process ingest queue
uv run sentiment-api daemon   # Poll sources, push to queue
```

### Production deployment

See **docs/INSTALLATION_MANUAL.md** and **scripts/deploy/** for production install, update, and rollback. User: `sentimenter`. Data: `/srv/sentimenter/volumes/` (out-of-Docker).

### Option C: API in Docker

```bash
cd sentiment_api
docker compose up -d
# API at http://localhost:8080
# Prometheus at http://localhost:9090
# Grafana at http://localhost:3001 (admin/admin)
```

### Option D: With frontend dashboard

```bash
cd sentiment_api
docker compose up -d
# API at http://localhost:8080, Dashboard at http://localhost:3000
# Or run frontend locally: cd frontend && npm run dev
```

### Option E: Frontend-only stack (minimal: postgres, redis, api, frontend)

```bash
cd sentiment_api
docker compose -f docker-compose.frontend_only.yml up -d
# API at http://localhost:8080, Dashboard at http://localhost:3000
# No worker, daemon, or observability stack
```

## API Key

All endpoints except `/v1/health` require an API key validated against `api_keys` table:
- Create key: `uv run python scripts/create_api_key.py`
- Header: `X-API-Key: <your-key>`
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
- `GET /v1/news/clusters/{cluster_id}` — Cluster drilldown (`include_asset_impacts`)
- `GET /v1/impacts/latest` — Latest winners/losers (markets/sectors/tickers)
- `GET /v1/impacts/clusters/{cluster_id}` — Asset targeting for cluster
- `GET /v1/universes` — Universe list
- `GET /v1/universes/{id}/constituents` — Constituents (paged)
- `GET /v1/sectors` — Sector taxonomy
- `GET /v1/research/spy/event-study` — Event studies
- `POST /v1/ask` — RAG query
- `POST /v1/admin/ingest/run` — Trigger ingest (operator)
- `GET /v1/sources` — Source registry
- `GET /v1/health` — Health check (no auth)
- `GET /metrics` — Prometheus metrics (no auth)
- `GET /ready` — Readiness probe (DB ready)
- `POST /v1/admin/backfill` — Backfill by date range

CLI: `sentiment-api backfill --from YYYY-MM-DD --to YYYY-MM-DD`  
CLI: `sentiment-api retention --days N`
