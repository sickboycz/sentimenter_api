# Implementation Gap Analysis — sentiment_api v1.1

**Date:** 2026-02-02  
**Specs:** SENTIMENT_API_MASTER_SPEC_v1.1, SENTIMENT_API_SCOPE_TECH_SPEC_v1.1_PRD, tech packages v1.0/v1.1  
**Focus:** Error handling, health gates, health monitoring, restart matrix, M10 ops

---

## 1) Executive Summary

| Area | Status | Notes |
|------|--------|------|
| **Error handling** | ✓ | Retries+backoff, circuit breaker, daemon run ledger |
| **Health endpoint** | ✓ | AC-M10.4 met (Postgres, Redis, Registry) |
| **Health gates** | ✓ | Single endpoint (ok/degraded/down) |
| **Health monitoring** | ✓ | /metrics Prometheus; queue, ingestion, translation, API |
| **Restart matrix** | ✓ | Docker restart:on-failure; systemd API/worker/daemon |

---

## 2) Acceptance Criteria Cross-Check

### M0 — Source Registry
| AC | Status | Notes |
|----|--------|------|
| AC-M0.1 | ✓ | Registry validates schema; raises RegistryError on invalid config |
| AC-M0.2 | ✓ | Duplicate source_id rejected |
| AC-M0.3 | ✓ | Per-source enable/disable via registry |
| AC-M0.4 | ✓ | Pack enable/disable |
| **Hot reload** | ✓ | Daemon: periodic reload every 10 cycles; SIGHUP triggers reload |

### M1 — Collectors
| AC | Status | Notes |
|----|--------|------|
| AC-M1.1 | — | p95 fetch &lt; 10 min (no instrumentation) |
| AC-M1.2 | ✓ | Items have required fields |
| AC-M1.3 | ✓ | Retries+backoff in http_client; circuit breaker; daemon records failures in runs |
| AC-M1.4 | — | Backfill by date range not implemented |

### M10 — Observability & Ops
| AC | Status | Notes |
|----|--------|------|
| AC-M10.1 | ✓ | ingestion_lag_seconds, ingestion_errors_total on /metrics |
| AC-M10.2 | ✓ | translation_failures_total on /metrics |
| AC-M10.3 | ✓ | queue_depth on /metrics; api_latency_ms_avg, api_errors_total |
| AC-M10.4 | ✓ | Health endpoint exposes Postgres, Redis, Registry |

---

## 3) Error Handling

### Implemented
- API: `asyncpg.UndefinedTableError` caught on data endpoints; returns empty/default.
- API: DB pool init failure → API still starts (graceful).
- Worker: `process_summarize` failures → `finish_run(..., "fail", {"error": str(e)})`.
- Worker: Asset targeting, outcomes → wrapped in try/except, logged.
- Daemon: Poll exceptions → logged; loop continues.
- Collectors: Exceptions logged; iterator yields nothing.
- Registry: `RegistryError` on invalid config (API uses `_get_registry()` and tolerates None).

### Gaps
1. **No retries** — RSS, GDELT, Scrape: single attempt, no backoff on 429/5xx.
2. **No circuit breaker** — Repeated source failures don’t pause polling.
3. **Daemon run ledger** — On `poll_source` exception, no `insert_run` + `finish_run(status="fail")`; run ledger is incomplete.
4. **API key validation** — 401 on invalid key; error shape per schema.
5. **HTTP 429/5xx** — No exponential backoff in collectors.

---

## 4) Health Gates & Monitoring

### Health Endpoint (`GET /v1/health`)
- **Checks:** Postgres, Redis, Registry.
- **Status:** `ok` | `degraded` | `down`.
  - `down` when Postgres fails.
  - `degraded` when Redis or Registry fails.
- **Auth:** None (for orchestrators).

### Gaps
1. **Readiness vs liveness** — Single endpoint; no distinct readiness (e.g. DB ready) vs liveness.
2. **Startup gate** — API starts even if DB fails; no explicit readiness probe before serving.
3. **Artifact store** — Not checked (e.g. disk space, write test).
4. **OpenAI** — Not checked (optional dependency).

### Metrics (AC-M10.1, M10.2, M10.3)
- **Missing:** Prometheus or similar metrics.
- **Runbook expects:**
  - `ingestion_lag_seconds{source_id}`
  - `ingestion_errors_total{source_id}`
  - `translation_failures_total{source_id}`
  - `queue_depth{name}`
  - `api_latency_ms{route}`
  - `api_errors_total{route,code}`

---

## 5) Restart Matrix

### Docker Compose (`sentiment_api/docker-compose.yml`)
- **Postgres, Redis:** Health checks.
- **API, Worker, Daemon:** No `restart` policy.
- **Gap:** Containers exit and stay stopped on crash.

### systemd (`ops/sentiment_api.service`)
- **Restart=always, RestartSec=2** — only for API.
- **Gaps:**
  - No separate units for worker/daemon.
  - Runbook describes API, worker, Postgres, Redis, artifacts but only one service file.

### Recommended Restart Matrix
| Service | Restart | RestartSec | Notes |
|---------|---------|------------|-------|
| API | always | 2 | ✓ in template |
| Worker | always | 5 | Add; allow queue drain |
| Daemon | always | 10 | Add; backoff on repeated failures |

---

## 6) Run Ledger (runs table)

- **Implemented:** `insert_run`, `finish_run` with `status` and `error` JSON.
- **Worker:** Ingest, summarize, index runs recorded; failures recorded for summarize.
- **Daemon:** Only records runs when `count > 0`; failures are not recorded.
- **Gap:** Per-source failure history incomplete for operator dashboards.

---

## 7) Implementation Complete (2026-02-02)

### Implemented
1. **Restart policies** — `restart: on-failure` on Docker Compose api, worker, daemon.
2. **Daemon run ledger** — Failed polls recorded via `insert_run` + `finish_run(status="fail")`.
3. **systemd units** — `sentiment_api.service`, `sentiment_api_worker.service`, `sentiment_api_daemon.service` (ops/ + Docs package).
4. **Collector retries** — `fetch_with_retry()` in collectors/http_client.py; 3 retries, exponential backoff for 429/5xx.
5. **Metrics** — `GET /metrics` Prometheus: ingestion_errors_total, ingestion_lag_seconds, translation_failures_total, queue_depth, api_latency_ms_avg, api_errors_total.
6. **Circuit breaker** — Per-source; skip after 5 failures, 5min cooldown.
7. **M0 hot reload** — Daemon: periodic registry reload every 10 cycles; SIGHUP triggers immediate reload.

---

## 8) Implementation Status Overview

| Module | Status | Notes |
|--------|--------|-------|
| M0 | ✓ | Hot reload missing |
| M0.5 | ✓ | Universe + sectors |
| M1 | Partial | No retries, circuit breaker; partial error ledger |
| M2 | ✓ | Translation, provenance |
| M3 | ✓ | Dedup, clustering |
| M4 | ✓ | Summaries L1–L4 |
| M5 | ✓ | Impact engine |
| M5.5 | ✓ | Asset targeting, audit |
| M6 | ✓ | Index engine |
| M7 | ✓ | Embeddings, pgvector |
| M8 | ✓ | Research engine |
| M9 | ✓ | API, auth, pagination |
| M10 | Partial | Health ✓; metrics ✗ |
