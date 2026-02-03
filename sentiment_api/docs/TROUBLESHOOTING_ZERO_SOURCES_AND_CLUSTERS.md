# Troubleshooting: 0 Sources and 0 Clusters

## Symptoms

- **Registry / Sources page:** "0 sources" from `/v1/sources`
- **News Feed:** "No clusters yet"
- **System counts:** articles > 0 (e.g. 161), clusters = 0, events = 0, summaries possibly > 0 (e.g. 16)
- **Queue:** All backlogs 0; worker last job e.g. `sentiment_api:ingest`
- **Topbar:** API ok, Auth ok, Ingestion: unknown, Allocation: unknown

---

## 1. Why "0 sources"?

`/v1/sources` returns data from the **source registry file**, not from the DB. The API loads:

- Path: `SOURCE_REGISTRY_PATH` (default `Docs/.../source_registry.yaml`; in Docker: `/etc/sentiment_api/source_registry.yaml`)
- If the file is missing or invalid → health/registry fails and `/v1/sources` can return 503 REGISTRY_UNAVAILABLE
- If the file loads but has **no enabled sources** → response is 200 with `data: []` → UI shows "0 sources"

**Checks on the server:**

```bash
# 1. Registry file present and mounted (in api container)
docker compose -f docker-compose.yml -f docker-compose.production.yml exec api ls -la /etc/sentiment_api/source_registry.yaml

# 2. File has content and "sources:" with entries
docker compose -f docker-compose.yml -f docker-compose.production.yml exec api head -80 /etc/sentiment_api/source_registry.yaml

# 3. Packs enabled (defaults.enabled and packs.*.enabled)
docker compose -f docker-compose.yml -f docker-compose.production.yml exec api grep -A2 "packs:" /etc/sentiment_api/source_registry.yaml
```

**Fixes:**

- Ensure the repo has `sentiment_api/registry/source_registry.yaml` with non-empty `sources:` and packs `enabled: true`.
- Production mount: `./registry/source_registry.yaml:/etc/sentiment_api/source_registry.yaml:ro`. So from the compose dir, `registry/source_registry.yaml` must exist and be the full registry (not an empty override).
- If you use a custom registry path, set `SOURCE_REGISTRY_PATH` in the API (and worker/daemon) env to that path and mount the file there.

---

## 2. Why 0 clusters with articles and some summaries?

Pipeline: **ingest → normalize → summarize → (cluster + event + embedding) → index**.

- **161 articles** → ingest/normalize ran.
- **16 summaries** → 16 summarize jobs completed at least up to `insert_summary` (L1/L2/L3).
- **0 clusters, 0 events** → no row ever inserted into `clusters` / `events`. So either:
  - Summarize jobs are **failing after L2** (e.g. embedding, LLM, or DB) before `insert_cluster`, or
  - They **fail at** `insert_cluster` / `add_cluster_member` / `insert_embedding` (e.g. DB schema, pgvector, constraint).

**Checks on the server:**

```bash
# 1. Worker logs (look for DB/cluster errors)
docker compose -f docker-compose.yml -f docker-compose.production.yml logs worker --tail 200

# Look for:
# - "DB connection OK (clusters and embeddings tables present)"  → startup check passed
# - "Clustering DB error (insert_cluster/...)"                   → cluster step failing
# - Any asyncpg / pgvector / constraint tracebacks

# 2. Tables and pgvector
docker compose -f docker-compose.yml -f docker-compose.production.yml exec postgres \
  psql -U sentiment -d sentiment -c "\dt clusters embeddings; SELECT COUNT(*) FROM clusters; SELECT COUNT(*) FROM embeddings;"

# 3. Embeddings table schema (pgvector)
docker compose -f docker-compose.yml -f docker-compose.production.yml exec postgres \
  psql -U sentiment -d sentiment -c "\d embeddings"
```

**Fixes:**

- **Worker never gets to cluster step:** Fix LLM/embedding (e.g. OPENAI_API_KEY, model, rate limits). Check logs for summarize-step failures.
- **"Clustering DB error" or traceback in cluster step:**  
  - Run migrations so `clusters` and `embeddings` exist and match the app (including pgvector extension and `embedding` column type).  
  - If you added `_verify_db_connection()` and the worker now crashes at startup with "Clustering tables missing", run the same migrations.
- **pgvector:** Ensure the DB has the pgvector extension and that `embeddings.embedding` is `vector(N)` with the expected dimension (e.g. 3072 for `text-embedding-3-large`).

---

## 3. Diagnostic script

From the server (from `sentiment_api/`):

```bash
./scripts/diagnose-pipeline.sh -f docker-compose.yml -f docker-compose.production.yml
```

This prints: Postgres counts (articles, clusters, events, summaries, runs, embeddings), Redis queue lengths, registry file presence in the API container, embeddings table columns, and worker last-job info from Redis.

---

## 4. Quick checklist

| Check | Command / action |
|-------|-------------------|
| Registry file on API | `exec api cat /etc/sentiment_api/source_registry.yaml \| head -50` |
| Sources in registry | YAML has `sources:` with entries and packs `enabled: true` |
| Worker startup | Logs show "DB connection OK" and "Worker started, synced N sources" |
| Worker cluster errors | Logs show "Clustering DB error" or traceback → fix DB/migrations/pgvector |
| Tables | `clusters` and `embeddings` exist; `embeddings.embedding` is vector type |
| Queue backlog | If summarize backlog stays 0 and no new clusters, worker may be failing on each summarize job → check logs |

---

## 5. Ingestion / Allocation "unknown"

Topbar status pills often derive from:

- **API:** health endpoint
- **Ingestion:** e.g. sources count or daemon/worker activity
- **Allocation:** e.g. tickers/impacts data

If registry has 0 sources, "Ingestion: unknown" is consistent. Fixing the registry (so sources > 0) and ensuring the worker and daemon run with the same registry will improve ingestion visibility. Allocation depends on clusters/impacts; fixing 0 clusters as above should help.
