# Observability Runbook — sentiment_api

**Date:** 2026-02-02  
**Purpose:** Health monitoring, Prometheus, Grafana, and operational guidance.

---

## 1) Services

| Component | Port | Purpose |
|-----------|------|---------|
| **Prometheus** | 9090 | Metrics scrape (API /metrics) |
| **Grafana** | 3001 | Dashboards (login: admin/admin) |
| **Loki** | 3100 | Log aggregation |
| **Promtail** | 9080 | Log shipper → Loki |
| **Tempo** | 3200, 4317, 4318 | Traces (OTLP) |

---

## 2) Endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /v1/health` | No | Full health (postgres, redis, registry, artifacts, openai) |
| `GET /ready` | No | Readiness (DB pool) |
| `GET /metrics` | No | Prometheus text format |

---

## 3) Grafana Dashboards

Auto-provisioned from `infra/grafana/dashboards/`:

- **sentiment_api overview** — Request rate, latency, errors, queue depth
- **Health Monitoring** — API up, request rate, latency, errors, queue depth, ingestion lag, ingestion errors

**Access:** http://localhost:3001 (admin/admin)

---

## 4) Prometheus Scrape

- **Job:** `sentiment_api`
- **Target:** `api:8080`
- **Path:** `/metrics`
- **Interval:** 15s

**Metric names:**
- `up{job="sentiment_api"}` — 1 = healthy, 0 = down
- `api_requests_total{route,status}` — Request counter
- `api_latency_ms_avg{route}` — Latency gauge
- `api_errors_total{route,code}` — Error counter
- `queue_depth{name}` — Queue depth gauge
- `ingestion_lag_seconds{source_id}` — Ingestion lag
- `ingestion_errors_total{source_id}` — Ingestion errors

---

## 5) Health Gate Logic

1. **postgres** — Must be healthy before api, worker, daemon start.
2. **redis** — Must be healthy before api, worker, daemon start.
3. **api** — Must pass healthcheck (`/v1/health` returns status) before Prometheus is considered ready.
4. **prometheus** — Must be healthy before Grafana starts (datasource dependency).

---

## 6) Troubleshooting

| Symptom | Check |
|---------|-------|
| Grafana no data | Prometheus scraping API? Check `http://localhost:9090/targets` |
| API unhealthy | postgres/redis up? `docker compose ps` |
| Prometheus targets down | API reachable? `curl http://api:8080/metrics` from Prometheus container |
| Worker/daemon failing | Redis ping in healthcheck; check logs |
