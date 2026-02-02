# MASTER PROMPT — Cursor (Implement sentiment_api end-to-end)

You are Cursor, acting as a principal engineer. Your job is to **implement the entire sentiment_api system** described in this repository.

## Source of truth (do not deviate)
Treat these files as canonical requirements:

- `docs/original/0) Design principles (non-negotiable).md`
- `docs/original/1) Target outcome.md`
- `docs/original/SENTIMENT_API_MASTER_SPEC_v1.1.md`
- `docs/v1.2/01_SCOPE_TECH_SPEC_V1_2.md`
- `openapi/sentiment_api.openapi.v1.2.yaml`
- `openapi/schemas/*`
- `registry/sources.yaml`

If any code conflicts with these docs/contracts, **the code must be changed** (not the docs), unless explicitly instructed otherwise.

## Non-negotiable engineering rules
1) **Evidence-first**  
   Every score/output must trace back to sources (URLs + timestamps + extracted spans). Never emit unexplained scores.

2) **Schema-locked**  
   All API responses must match the JSON schemas in `openapi/schemas`. Use `extra="forbid"`.

3) **No local LLM runtime on IBKR side**  
   LLM/RAG happens only in sentiment_api. IBKR consumes via HTTP.

4) **English-first output**  
   Serve English fields; translate where needed. Store original language separately.

5) **Ticker whitelist**  
   The system must never output a ticker that is not present in `ticker_universe`.

6) **Idempotency**  
   All ingestion writes are idempotent (dedupe keys, unique constraints). Any future POST endpoints must support `Idempotency-Key`.

7) **Robots/ToS compliance**  
   Implement polite crawling; never bypass paywalls; store metadata/snippets when licensing is unclear.

8) **Forward evaluation**  
   Store expectations at event time; measure realized outcomes later; do not tune on hindsight.

## What you must deliver (completion definition)
### Backend (FastAPI)
- Implement all endpoints in OpenAPI v1.2:
  - `/api/sp-sentiment` (Moodix-compatible export)
  - `/v1/mood/now`
  - `/v1/index/intraday`
  - `/v1/news/clusters` and `/v1/news/clusters/{cluster_id}`
  - `/v1/impacts/latest` and `/v1/impacts/clusters/{cluster_id}`
  - `/v1/universes` and `/v1/universes/{universe_id}/constituents`
  - `/v1/sectors`
  - `/v1/topics/index`
  - `/v1/stream/events` (SSE)
  - `/v1/health`
  - `/metrics`

- Implement:
  - Request/response envelopes
  - Auth (X-API-Key or api_key)
  - Rate limiting (spec rules)
  - Error model (no stack traces)
  - Validation rules + invariants
  - DB repositories (Postgres)
  - Ingestion pipeline skeleton (collect → normalize → dedupe → cluster)
  - RAG summarization skeleton (schema-locked output)
  - Impact engine producing:
    - most affected market
    - sector impacts
    - winners/losers tickers (S&P500 + Nasdaq Composite universes)
  - Topic index computation

### Database
- Apply `backend/db/migrations/*` in order.
- Ensure uniqueness constraints + foreign keys enforce idempotency & ticker whitelist.

### Observability
- Prometheus metrics from API
- Grafana/Loki/Tempo stack works via `docker-compose.yml`
- All containers have health checks
- Correlate logs with request_id

### Frontend
- Implement the UI described in `docs/v1.2/03_FRONTEND_DASHBOARD_SPEC_V1_2.md`:
  - glassy shell
  - left rail navigation
  - overview charts
  - news feed + drilldown
  - impacts (markets/sectors/tickers)
  - topics
  - research
  - ops page
- Use runtime validation (Zod) for API responses
- Use polling + SSE (auto reconnect) to refresh

### Tests
- Make **all non-skipped tests pass**:
  - `backend/tests/test_contract_responses.py`
  - `backend/tests/test_openapi_refs.py`
  - `backend/tests/test_auth_and_error_envelope.py`
  - `backend/tests/test_topics_and_metrics.py`
  - `backend/tests/test_sse_stream.py`
- Unskip and implement:
  - `backend/tests/test_rate_limiting_spec.py`
  - `backend/tests/test_invariants_spec.py`

## Implementation order (do in this sequence)
Follow `docs/v1.2/06_IMPLEMENTATION_ORDER_V1_2.md`.

## Quality gates (must hold)
- Every endpoint returns schema-valid JSON
- Idempotency: repeated ingestion does not duplicate rows
- Rate limiting works and is tested
- Rollback plan documented + migrations are reversible (when possible)
- Observability dashboards show API traffic/latency
- Threat model mitigations implemented (SSRF block, injection hardening)

## How to work
- Make changes directly in the repo files.
- Prefer adding small, testable modules.
- Keep commands in README up to date.
- Add golden response fixtures where useful.

## Final deliverable
When done, provide:
- a brief summary of what changed
- how to run the stack
- how to run tests
- evidence checklist completion status
