# Ops Runbook — sentiment_api v1.0

This is the operator guide for a single-server deployment (recommended v1).

## 1) Runtime components
- API service: `sentiment_api_api`
- Worker service(s): `sentiment_api_worker`
- Postgres (with pgvector): `postgres`
- Redis (queue + cache): `redis`
- Artifact store: local directory (default `/data/artifacts`)

## 2) Required environment variables (minimum)
### API
- `SENTIMENT_API_ENV=prod|dev`
- `DATABASE_URL=postgresql://...`
- `REDIS_URL=redis://...`
- `ARTIFACT_ROOT=/data/artifacts`
- `SOURCE_REGISTRY_PATH=/etc/sentiment_api/source_registry.yaml`
- `API_KEY_HASH_SALT=...` (or use argon2 params)
- `OPENAI_API_KEY=...` (if using OpenAI model provider)
- `MODEL_SUMMARIZER_ID=openai:<model>`
- `MODEL_EMBEDDING_ID=openai:<embedding_model>`
- `DEFAULT_TIMEZONE=UTC`

### Budgets / caps
- `MAX_TOKENS_PER_MINUTE=...`
- `MAX_REQUESTS_PER_MINUTE=...`
- `MAX_ARTICLES_PER_SOURCE_PER_DAY=...`

## 3) Process supervision
### Option A: docker-compose
Use `ops/docker-compose.yml` as a starting point.

### Option B: systemd
Use `ops/sentiment_api.service` templates.

## 4) Logging & metrics
### Logs
- JSON logs to stdout (preferred)
- Include: request_id, run_id, source_id, article_id, cluster_id, durations, error codes.

### Metrics (Prometheus recommended)
- ingestion_lag_seconds{source_id}
- ingestion_errors_total{source_id}
- translation_failures_total{source_id}
- clustering_new_clusters_total
- clustering_updates_total
- queue_depth{name}
- api_latency_ms{route}
- api_errors_total{route,code}

## 5) Backups
### Database
- nightly `pg_dump` (compressed)
- keep 7 daily + 4 weekly + 12 monthly

### Artifacts
- rsync or tar+zstd for `/data/artifacts`
- ensure storage has enough headroom (HTML snapshots grow fast)

### Restore drill
- monthly restore into staging
- verify API endpoints respond and sample clusters render.

## 6) Security
- All /v1 endpoints require API key (header preferred).
- Health endpoint can be unauthenticated for orchestrators.
- Store only key hashes.
- Rate-limit per key.
- Do not store paywalled full text unless licensed.

## 7) Incident playbook
### Collector failures (per source)
1. Check `/v1/health` dependencies
2. Check run ledger (`runs` table) for source_id errors
3. Disable source in registry and reload (no deploy)
4. Investigate robots/ToS or parser profile drift.

### DB high load
- Reduce update intervals, tighten filters, disable optional packs, increase indexes.

### Index lag
- Check queue depth and worker concurrency.
- Increase worker replicas or reduce expensive model calls via caching.

