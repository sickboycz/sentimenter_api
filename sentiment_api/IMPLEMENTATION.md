# sentiment_api — Implementation Status

Implementation follows `Docs/sentiment_api_tech_package_v1.1/SENTIMENT_API_MASTER_SPEC_v1.1.md`. **v1.1** adds universe registry, asset targeting (markets/sectors/tickers).

## Modules

| Module | Status | Description |
|--------|--------|-------------|
| M0  | ✓ | Source Registry loader + validator (YAML/JSON, schema) |
| M1  | ✓ | Collectors: RSS, GDELT DOC 2.0, Scrape |
| M2  | ✓ | Normalization: canonical URL, lang detect, translation (pluggable) |
| M3  | ✓ | Dedup: article_id, content hash; Clustering: embedding similarity |
| M4  | ✓ | Summaries L1–L4: LLM (OpenAI) or rule-based fallback |
| M5  | ✓ | Impact engine: formula-based scoring |
| M6  | ✓ | Index engine: intraday + daily OHLC, Moodix-compatible |
| M7  | ✓ | Embeddings: OpenAI text-embedding-3-large or mock |
| M8  | ✓ | Research engine: event studies vs SPY/ES |
| M9  | ✓ | API: all endpoints per OpenAPI |
| M10 | ✓ | Health, metrics, observability |

## Pipeline

1. **Daemon** polls enabled sources (RSS/GDELT/scrape), pushes raw items to `sentiment_api:ingest`.
2. **Worker** pops from queue:
   - Normalize (URL, lang, translate)
   - Insert article (dedupe by article_id)
   - L1/L2 summary, embed, cluster (or create new)
   - L3 cluster summary, impact score
   - Insert cluster, event, embeddings
   - Push to index queue
3. **Index worker** computes intraday ticks and daily OHLC.

## API Endpoints

- `GET /api/sp-sentiment` — Moodix-compatible daily series
- `GET /v1/mood/now` — Current mood snapshot
- `GET /v1/index/intraday` — Intraday index (1m/5m/15m/1h)
- `GET /v1/news/clusters` — Story clusters (filterable)
- `GET /v1/news/clusters/{id}` — Cluster drilldown
- `GET /v1/research/spy/event-study` — Event studies
- `GET /v1/impacts/latest` — Latest news → winners/losers (markets/sectors/tickers)
- `GET /v1/impacts/clusters/{id}` — Asset targeting for cluster
- `GET /v1/universes` — Universe list
- `GET /v1/universes/{id}/constituents` — Constituents (paged)
- `GET /v1/sectors` — Sector taxonomy (GICS-like 11)
- `POST /v1/ask` — RAG query (vector retrieval + LLM answer with citations)
- `POST /v1/admin/ingest/run` — Trigger ingest (operator)
- `GET /v1/sources` — Source registry
- `GET /v1/health` — Health (no auth)

CLI: `sentiment-api refresh-universes` — Refresh universe constituents (idempotent)

## Implemented Elements

- **Translation**: OpenAI for non-English content (required)
- **API keys**: Validated against `api_keys` table (argon2 or SHA256)
- **L0 artifacts**: article_bodies, object store paths
- **Summaries**: L1–L4 persisted in summaries table with dedupe_key
- **Expectations/outcomes**: Forward eval ledger, outcome measurement
- **Runs**: Audit for ingest, summarize, score, index
- **Embeddings**: OpenAI or sentence-transformers fallback (3072-dim padded)
- **Asset targeting (M5.5)**: Rule-based + optional LLM; event_impacts; cluster_asset_targeting_audit for full scoring
- **Universe refresh**: `refresh-universes` CLI; GICS-like 11 sectors + unknown
- **Error handling**: Retries+backoff (429/5xx) in collectors; circuit breaker per source; daemon run ledger for failures
- **Metrics**: `GET /metrics` Prometheus (ingestion_errors, ingestion_lag, translation_failures, queue_depth, api_latency, api_errors)
- **M0 hot reload**: Daemon periodic registry reload + SIGHUP
- **Restart**: Docker `restart: on-failure`; systemd API/worker/daemon service files in ops/

## Run

```bash
# API only
uv run sentiment-api api

# Full stack (3 terminals)
uv run sentiment-api api
uv run sentiment-api worker
uv run sentiment-api daemon

# Or Docker
docker compose up -d
```

## Dependencies

- Postgres 15+ with pgvector
- Redis
- OpenAI API key (optional; mock used when absent)
