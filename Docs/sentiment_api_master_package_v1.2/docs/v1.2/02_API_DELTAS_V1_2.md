# API deltas — v1.2

This file defines what changes vs v1.1.

## Keep (v1.0/v1.1)
- Moodix-compatible export:
  - `GET /api/sp-sentiment`
- Core v1:
  - `GET /v1/mood/now`
  - `GET /v1/index/intraday`
  - `GET /v1/news/clusters`
  - `GET /v1/news/clusters/{cluster_id}`
  - `GET /v1/research/spy/event-study`
  - `GET /v1/sources`
  - `GET /v1/health`
- v1.1 impacts targeting:
  - `GET /v1/impacts/latest`
  - `GET /v1/impacts/clusters/{cluster_id}`
  - `GET /v1/universes`
  - `GET /v1/universes/{universe_id}/constituents`

## Add (v1.2)
### 1) Topic indices
- `GET /v1/topics/index`
  - mood/topic contribution timeline

### 2) Streaming
- `GET /v1/stream/events` (SSE)
  - emits events: heartbeat, cluster_updated, mood_updated, impacts_updated, topics_updated

### 3) Metrics
- `GET /metrics` (Prometheus scrape)

## Idempotency
- All list endpoints must be idempotent by nature.
- Any POST/trigger endpoints (if added later) must accept `Idempotency-Key` header and store key→result mapping.

## Rate limiting
- 60 req/min per api_key default.
- 10 req/min for heavy research ranges.
- 10 concurrent SSE streams per api_key.

## Error envelopes
All `/v1/*` JSON endpoints return the common envelope:

```json
{
  "meta": {"request_id": "req_...", "as_of": "2026-02-02T00:00:00Z"},
  "data": { },
  "errors": []
}
```
