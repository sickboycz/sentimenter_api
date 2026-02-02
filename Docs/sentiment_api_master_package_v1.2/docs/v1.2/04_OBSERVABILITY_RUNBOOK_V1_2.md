# Observability runbook — v1.2 (Prometheus + Grafana + Loki + Tempo)

## Services
- Prometheus: metrics scrape
- Grafana: dashboards
- Loki: logs
- Tempo: traces (OTLP)
- Promtail: ships logs → Loki

## Required endpoints
- API: `/v1/health` (readiness), `/metrics`
- Frontend: `/api/health` (Next.js route)
- Worker/Scheduler: healthcheck defined in Docker

## Key dashboards
- API traffic + p95 latency
- Ingestion:
  - lag by source_id
  - error rate by source_id
- Pipeline:
  - translation fails
  - clustering throughput
  - allocation failures
- Impact:
  - distribution of L0..L5
  - winners/losers changes per hour
- Topic indices:
  - top contributing topics
- Infra:
  - CPU/memory container stats (optional with node exporter)

## Alerts (recommended)
- API down (healthcheck fails)
- DB connection failures
- ingestion lag p95 > 20 minutes for >15 minutes
- allocation_failed > 2% over 30 minutes
- translate_failed spike > baseline

## Acceptance criteria
- AC-OBS1: dashboards auto-provision (no manual steps).
- AC-OBS2: logs correlated by request_id/trace_id.
- AC-OBS3: healthchecks prevent broken containers from being “healthy”.
