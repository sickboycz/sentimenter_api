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
# If "logs worker" hangs or returns nothing, use the container name:
docker ps -a --format "{{.Names}}" | grep worker
docker logs <worker_container_name> --tail 300

# Or with compose (from sentiment_api/):
docker compose -f docker-compose.yml -f docker-compose.production.yml logs worker --tail 200 2>&1 | cat

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

## 4. Fix-everything script

From the **server** (run as root or with sudo):

```bash
cd /srv/sentimenter/repo/sentiment_api
sudo ./scripts/fix-everything.sh --production --fix-git --pull --rebuild --restart
```

This script can:

- **--fix-git** — Add repo to `git safe.directory` (fixes "dubious ownership" when pulling)
- **--pull** — `git fetch` + `git pull`
- **--rebuild** — `docker compose build --no-cache` (all services)
- **--rebuild-worker** — Rebuild only the worker image (faster after worker-only code changes)
- **--restart** — `docker compose up -d` and restart `sentimenter-docker` unit
- **--no-diagnose** — Skip running the pipeline diagnostics at the end

Without options it only runs diagnostics. Full one-shot deploy: `--production --fix-git --pull --rebuild --restart`.

---

## 5. Quick checklist (manual)

| Check | Command / action |
|-------|-------------------|
| Registry file on API | `exec api cat /etc/sentiment_api/source_registry.yaml \| head -50` |
| Sources in registry | YAML has `sources:` with entries and packs `enabled: true` |
| Worker startup | Logs show "DB connection OK" and "Worker started, synced N sources" |
| Worker cluster errors | Logs show "Clustering DB error" or traceback → fix DB/migrations/pgvector |
| Tables | `clusters` and `embeddings` exist; `embeddings.embedding` is vector type |
| Queue backlog | If summarize backlog stays 0 and no new clusters, worker may be failing on each summarize job → check logs |

---

## 6. Worker only processing ingest (0 clusters, 0 embeddings)

If worker logs show only **daemon polling** and **ingest** activity (no `process_summarize`, clustering, or embedding logs), the worker was likely **never taking from the summarize queue** because it checked ingest first and the daemon kept ingest non-empty.

**Fix (in code):** The worker’s `blpop` queue order was changed to prefer **summarize → index → score → ingest → normalize**, so downstream queues (summarize, cluster, embed) are drained before more ingest work. Rebuild and restart the worker after pulling this change:

```bash
cd /srv/sentimenter/repo/sentiment_api
sudo ./scripts/fix-everything.sh --production --pull --rebuild-worker --restart
```

After deploy, new articles will flow: ingest → summarize → clusters/embeddings. Existing articles that were never summarized need a backfill (see below).

---

## 7. Backfill summarize (existing articles → clusters)

If you have **articles in DB but 0 clusters** (e.g. before the queue-order fix), run `backfill_summarize` to push those articles into the summarize queue. The worker will then process them and create clusters.

```bash
# From host, inside the api container:
docker compose -f docker-compose.yml -f docker-compose.production.yml exec api python /app/scripts/backfill_summarize.py

# Dry-run first (log only, no push):
docker compose ... exec api python /app/scripts/backfill_summarize.py --dry-run

# Limit to 50 articles:
docker compose ... exec api python /app/scripts/backfill_summarize.py --limit 50
```

**Forensic logs:** After deploy, worker logs now include `Summarize: starting article X`, `Ingest: article X inserted, pushed to summarize`, `Summarize: cluster Y created`. Use these to trace the pipeline:

```bash
docker exec $(docker ps -q -f name=worker) grep -E 'Summarize:|Ingest:|Clustering DB error' /data/logs/worker.log | tail -100
```

---

## 8. Ingestion / Allocation "unknown"

Topbar status pills often derive from:

- **API:** health endpoint
- **Ingestion:** e.g. sources count or daemon/worker activity
- **Allocation:** e.g. tickers/impacts data

If registry has 0 sources, "Ingestion: unknown" is consistent. Fixing the registry (so sources > 0) and ensuring the worker and daemon run with the same registry will improve ingestion visibility. Allocation depends on clusters/impacts; fixing 0 clusters as above should help.
