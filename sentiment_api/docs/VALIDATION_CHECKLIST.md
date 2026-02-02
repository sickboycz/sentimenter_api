# sentiment_api — Validation Checklist

**Version:** 1.2  
**Date:** 2026-02-02  
**Purpose:** Production-ready validation before release or deployment.

---

## 1. Automated Checks (run scripts/validation/run.sh)

| Check | Command | Expected |
|-------|---------|----------|
| Pytest (unit + contract) | `uv run pytest tests/ -v --ignore=tests/test_sse_stream.py` | 0 failures |
| Docker Compose config | `docker compose -f docker-compose.yml config -q` | Exit 0 |
| Docker Compose production | `docker compose -f docker-compose.yml -f docker-compose.production.yml config -q` | Exit 0 |
| OpenAPI schema exists | `test -f openapi/sentiment_api.openapi.v1.2.yaml` | Exists |
| Required files | Schema in schemas/, infra configs | All present |

---

## 2. API Contract Validation

| Endpoint | Method | Auth | Response Schema |
|----------|--------|------|-----------------|
| `/v1/health` | GET | No | meta, data, errors |
| `/ready` | GET | No | 200 "ok" / 503 |
| `/metrics` | GET | No | Prometheus text |
| `/v1/mood/now` | GET | Yes | MoodNow response |
| `/v1/impacts/latest` | GET | Yes | AssetImpactBundle |
| `/v1/topics/index` | GET | Yes | TopicsIndex response |
| `/v1/stream/events` | GET | Yes | SSE text/event-stream |

---

## 3. Security & Invariants

| Check | Status |
|-------|--------|
| API key required on protected routes | ✓ |
| Error envelope (meta, data, errors) | ✓ |
| Rate limiting (60/min default, 10 research, 10 SSE) | ✓ |
| SSRF block (private IPs, localhost) | ✓ |
| Ticker whitelist (winners/losers from universes) | ✓ |
| Idempotency-Key on POST ask/ingest/backfill | ✓ |

---

## 4. Observability

| Check | Status |
|-------|--------|
| Prometheus scrape target (api:8080/metrics) | ✓ |
| Grafana dashboards provisioned | ✓ |
| Health check on API | ✓ |
| Restart policies (postgres/redis always, others on-failure) | ✓ |

---

## 5. Deployment

| Check | Status |
|-------|--------|
| docker-compose.production.yml (out-of-Docker volumes) | ✓ |
| install.sh, update.sh, rollback.sh | ✓ |
| /etc/sentimenter/env for secrets | ✓ |
| User sentimenter, /srv/sentimenter/volumes/ | ✓ |

---

## 6. Manual Verification (with Docker stack running)

```bash
# Start stack
cd sentiment_api && docker compose up -d

# Health
curl -s http://127.0.0.1:8080/v1/health | head
curl -s http://127.0.0.1:8080/ready

# Metrics
curl -s http://127.0.0.1:8080/metrics | head

# Protected (with API key)
curl -s -H "X-API-Key: test_key_1234567890abcdef" http://127.0.0.1:8080/v1/mood/now
curl -s -H "X-API-Key: test_key_1234567890abcdef" http://127.0.0.1:8080/v1/topics/index

# Prometheus
curl -s http://127.0.0.1:9090/-/ready

# Grafana
curl -s http://127.0.0.1:3001/api/health
```

---

## 7. Evidence Summary

| Category | Pass |
|----------|------|
| Pytest | ✓ |
| Docker config | ✓ |
| API contract | ✓ |
| Security/invariants | ✓ |
| Observability | ✓ |
| Deployment | ✓ |
