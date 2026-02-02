# sentiment_api — Docker, Prometheus & Architecture

**Version:** 1.2  
**Date:** 2026-02-02

---

## 1. Docker Structure

### 1.1 Compose Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full stack (postgres, redis, api, worker, daemon, frontend, prometheus, grafana, loki, promtail, tempo) |
| `docker-compose.frontend_only.yml` | Minimal stack (postgres, redis, api, frontend) — no worker, daemon, observability |
| `docker-compose.production.yml` | Override for production: bind mounts to `/srv/sentimenter/volumes/` |

### 1.2 Usage

```bash
# Full stack (dev)
docker compose up -d

# Frontend-only (dashboard + minimal backend)
docker compose -f docker-compose.frontend_only.yml up -d

# Production (out-of-Docker data)
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
```

### 1.3 Services Overview

| Service | Image / Build | Port(s) | Purpose |
|---------|---------------|---------|---------|
| **postgres** | pgvector/pgvector:pg15 | 5432 | Primary DB (pgvector for embeddings) |
| **redis** | redis:7 | 6379 | Queue + cache |
| **api** | build: Dockerfile | 8080 | FastAPI REST API |
| **worker** | build: . | — | Ingest queue processor |
| **daemon** | build: . | — | Source poller, pushes to queue |
| **frontend** | build: docker/frontend/Dockerfile | 3000 | Next.js dashboard |
| **prometheus** | prom/prometheus:v2.54.1 | 9090 | Metrics scrape |
| **grafana** | grafana/grafana:11.2.2 | 3001 | Dashboards |
| **loki** | grafana/loki:3.1.0 | 3100 | Log aggregation |
| **promtail** | grafana/promtail:3.1.0 | 9080 | Log shipper → Loki |
| **tempo** | grafana/tempo:2.6.1 | 3200, 4317, 4318 | Traces (OTLP) |

### 1.4 Dockerfiles

**API / Worker / Daemon** (`Dockerfile`):
```
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .
COPY sentiment_api ./sentiment_api
CMD ["python", "-m", "uvicorn", "sentiment_api.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Frontend** (`docker/frontend/Dockerfile`):
- Multi-stage: deps → build → production
- Base: node:20-alpine
- Output: Next.js production build on port 3000

### 1.5 Volumes

| Volume | Dev | Production |
|--------|-----|------------|
| postgres data | `pgdata` (named) | `/srv/sentimenter/volumes/postgres/data` |
| redis | (in-memory) | `/srv/sentimenter/volumes/redis` |
| artifacts | `artifacts` (named) | `/srv/sentimenter/volumes/artifacts` |
| logs | — | `/srv/sentimenter/volumes/logs` |
| grafana_data | `grafana_data` | `/srv/sentimenter/volumes/grafana_data` |
| loki_data | `loki_data` | `/srv/sentimenter/volumes/loki_data` |

### 1.6 Startup Order (Health Gates)

```
postgres (healthy) ──┬── redis (healthy)
                     │
                     ├── api (healthy) ──> prometheus (healthy) ──> grafana
                     ├── worker (postgres+redis healthy)
                     ├── daemon (postgres+redis healthy)
                     └── frontend (api started)
```

### 1.7 Directory Layout (Infra)

```
infra/
├── prometheus/
│   └── prometheus.yml
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/datasources.yml
│   │   └── dashboards/dashboards.yml
│   └── dashboards/
│       ├── sentiment_api_overview.json
│       └── health_monitoring.json
├── loki/
│   └── loki-config.yaml
├── promtail/
│   └── promtail-config.yml
└── tempo/
    └── tempo.yml
```

---

## 2. Prometheus Implementation

### 2.1 Scrape Configuration

**File:** `infra/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["prometheus:9090"]

  - job_name: sentiment_api
    metrics_path: /metrics
    static_configs:
      - targets: ["api:8080"]
```

- **Job `sentiment_api`** — scrapes `api:8080/metrics` every 15s
- **Job `prometheus`** — self-monitoring

### 2.2 API Metrics Endpoint

**Path:** `GET /metrics` (no auth)

The API exposes Prometheus text exposition format. Metrics are collected by middleware and a registry:

| Source | Logic |
|--------|-------|
| HTTP requests | `metrics_middleware` records latency, status, route |
| Redis queues | `/metrics` handler fetches queue depth at scrape time |
| Ingestion / translation | Collectors call `ingestion_errors_total`, `translation_failures_total`, etc. |

### 2.3 Metrics Exported

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `up` | — | `job` | 1 if scrape succeeds (Prometheus built-in) |
| `api_requests_total` | counter | route, status | Request count |
| `api_latency_ms_avg` | gauge | route | Average latency (ms) |
| `api_errors_total` | counter | route, code | Error count |
| `queue_depth` | gauge | name | Redis queue length (INGEST, SUMMARIZE, INDEX) |
| `ingestion_lag_seconds` | gauge | source_id | Seconds since last success |
| `ingestion_errors_total` | counter | source_id | Ingestion errors |
| `translation_failures_total` | counter | source_id | Translation failures |
| `fetch_duration_seconds_p95` | gauge | source_id | P95 fetch duration |

### 2.4 Grafana Datasources

**File:** `infra/grafana/provisioning/datasources/datasources.yml`

| Datasource | URL | Purpose |
|------------|-----|---------|
| Prometheus | http://prometheus:9090 | Metrics (default) |
| Loki | http://loki:3100 | Logs |
| Tempo | http://tempo:3200 | Traces |

### 2.5 Grafana Dashboards

| Dashboard | Purpose |
|-----------|---------|
| **sentiment_api overview** | Request rate, latency, errors, queue depth |
| **Health Monitoring** | API up, request rate, latency, errors, queue depth, ingestion lag, ingestion errors |

**Access:** http://localhost:3001 (admin/admin)

### 2.6 Metrics Flow

```
API (metrics_middleware + collect_metrics)
    │
    ▼
GET /metrics  ←── Prometheus (scrape every 15s)
    │
    ▼
Grafana (queries Prometheus)
```

---

## 3. Architecture

### 3.1 High-Level Overview

```
                    ┌─────────────┐
                    │   Frontend  │ :3000
                    │  (Next.js)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │     API     │ :8080
                    │  (FastAPI)  │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌─────▼─────┐      ┌────▼────┐
   │Postgres │       │   Redis   │      │ /metrics│
   │ (pg15   │       │  (queue,  │      │         │
   │pgvector)│       │  cache)   │      └────┬────┘
   └────┬────┘       └─────┬─────┘           │
        │                  │                 │
   ┌────▼────┐       ┌─────▼─────┐      ┌────▼────┐
   │ Worker  │       │  Daemon   │      │Prometheus│
   │ (ingest │       │ (source   │      │  :9090   │
   │ queue)  │       │  poller)  │      └────┬────┘
   └─────────┘       └───────────┘           │
                                        ┌────▼────┐
                                        │ Grafana │
                                        │  :3001  │
                                        └─────────┘
```

### 3.2 Data Flow

1. **Daemon** — Polls sources (RSS, GDELT, etc.) per registry config; pushes raw items to Redis `INGEST` queue
2. **Worker** — Consumes `INGEST`; normalizes, translates, clusters; writes to Postgres; pushes to `SUMMARIZE` / `INDEX` queues
3. **API** — Reads from Postgres; serves REST endpoints; records metrics
4. **Frontend** — Fetches API; displays dashboards; SSE for real-time updates
5. **Prometheus** — Scrapes API `/metrics`; Grafana queries Prometheus

### 3.3 Component Roles

| Component | Role |
|-----------|------|
| **API** | REST service, auth (API key), rate limit, idempotency, health, metrics |
| **Worker** | Async queue consumer; L0→L5 pipeline; LLM summaries; embeddings |
| **Daemon** | Cron-like source polling; circuit breaker per source |
| **Postgres** | Canonical store (clusters, impacts, universes, api_keys) |
| **Redis** | Queues (INGEST, SUMMARIZE, INDEX); idempotency cache; SSE concurrency |
| **Frontend** | React/Next.js; React Query; SSE; Zod validation |

### 3.4 Observability Stack

| Component | Role |
|-----------|------|
| **Prometheus** | Scrapes metrics from API |
| **Grafana** | Dashboards; queries Prometheus, Loki, Tempo |
| **Loki** | Log aggregation |
| **Promtail** | Ships container logs → Loki |
| **Tempo** | Distributed tracing (OTLP) |

### 3.5 Network

All services share the default Docker Compose network. Internal DNS: `postgres`, `redis`, `api`, `prometheus`, etc.

---

## 4. References

- **RESTART_MATRIX.md** — Restart policies, health checks
- **OBSERVABILITY_RUNBOOK.md** — Health monitoring, troubleshooting
- **INSTALLATION_MANUAL.md** — Production deployment
