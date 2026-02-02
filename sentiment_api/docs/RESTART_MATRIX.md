# Restart Matrix — sentiment_api

**Date:** 2026-02-02  
**Purpose:** Document restart policies and health gate logic for all services.

---

## 1) Restart Policies

| Service | Restart Policy | Rationale |
|---------|----------------|-----------|
| **postgres** | `always` | Core data store; must recover from crashes. |
| **redis** | `always` | Queue/cache; must stay up for ingestion. |
| **api** | `on-failure` | Stateless; restart on crash; let orchestrator handle. |
| **worker** | `on-failure` | Stateless; restart on crash; reconnects to Redis. |
| **daemon** | `on-failure` | Stateless; restart on crash; reconnects to Redis. |
| **frontend** | `on-failure` | Stateless; restart on crash. |
| **prometheus** | `on-failure` | Metrics; restart on crash. |
| **grafana** | `on-failure` | Dashboards; restart on crash. |
| **loki** | `on-failure` | Log aggregation; restart on crash. |
| **promtail** | `on-failure` | Log shipper; restart on crash. |
| **tempo** | `on-failure` | Tracing; restart on crash. |

---

## 2) Health Checks

| Service | Health Check | Interval | Timeout | Retries | Start Period |
|---------|--------------|----------|---------|---------|--------------|
| **postgres** | `pg_isready -U sentiment` | 5s | 5s | 5 | — |
| **redis** | `redis-cli ping` | 5s | 3s | 5 | — |
| **api** | `GET /v1/health` → grep status | 15s | 5s | 5 | 10s |
| **worker** | Redis ping (Python) | 30s | 5s | 3 | 15s |
| **daemon** | Redis ping (Python) | 30s | 5s | 3 | 15s |
| **frontend** | `GET /api/health` → grep ok | 10s | 5s | 6 | — |
| **prometheus** | `GET /-/ready` → grep ready | 10s | 5s | 6 | — |
| **grafana** | `GET /api/health` → grep ok | 10s | 5s | 6 | — |
| **loki** | `GET /ready` → grep ready | 10s | 5s | 6 | — |
| **promtail** | `GET /ready` | 10s | 5s | 3 | — |
| **tempo** | `GET /ready` | 10s | 5s | 3 | — |

---

## 3) Health Gates (Startup Order)

```
postgres (healthy) ──┬──> redis (healthy)
                     │
                     ├──> api (healthy) ──> prometheus (healthy) ──> grafana
                     │
                     ├──> worker (depends: api started, postgres+redis healthy)
                     │
                     ├──> daemon (depends: postgres+redis healthy)
                     │
                     └──> frontend (depends: api started)
```

- **API** waits for postgres + redis healthy before starting; exposes `/v1/health` and `/ready`.
- **Prometheus** waits for API healthy before starting (scrapes api:8080/metrics).
- **Grafana** waits for Prometheus healthy (datasource).
- **Worker/Daemon** wait for postgres + redis healthy; use Redis ping for healthcheck (process liveness).

---

## 4) Readiness vs Liveness

- **`/v1/health`** — Full dependency check (postgres, redis, registry, etc.). Used by API healthcheck.
- **`/ready`** — Minimal readiness (DB pool). Used for Kubernetes-style readiness probes.
- **Healthchecks** — Docker uses these to mark container healthy; `depends_on: condition: service_healthy` blocks until pass.
