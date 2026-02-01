# sentiment_api — Implementation Status

Implementation follows `Docs/sentiment_api_tech_package_v1.0/SENTIMENT_API_MASTER_SPEC_v1.0.md`.

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
- `POST /v1/ask` — RAG query (stub)
- `GET /v1/sources` — Source registry
- `GET /v1/health` — Health (no auth)

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
