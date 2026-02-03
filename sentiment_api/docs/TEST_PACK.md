# Test Pack

Comprehensive test pack: unit, API validation, integration, contract, and optional E2E.

## Run all tests

From `sentiment_api/`:

```bash
./scripts/run_tests.sh
```

- Runs all tests under `tests/`. E2E tests (`test_pipeline_e2e.py`) are **skipped** unless `SENTIMENT_E2E=1`.
- For full pass of contract/invariants/topics/mood/impacts: **Postgres** must be up and `DATABASE_URL` set; otherwise those tests may 503 (auth/DB).

## Run fast pack (no DB)

```bash
./scripts/run_tests.sh --fast
```

Runs **53 tests** that do not require Postgres or Redis:

- **Unit:** `tests/unit/` — embedding cache, chunk ingest, cross-encoder, repo L3 summary, rerank scoring, provider timeout
- **API:** `tests/test_api_cluster_and_retrieval.py` — GET cluster by id (400/404), POST retrieval/ingest (400), POST search/advanced (400)
- **Integration:** `tests/integration/test_advanced_search_pipeline.py` — Tier B rerank deterministic, cache hits
- **SSRF:** `tests/test_ssrf.py`
- **OpenAPI:** `tests/test_openapi_refs.py`
- **Contract (no DB):** health, status, metrics endpoint

## Run E2E

```bash
SENTIMENT_E2E=1 ./scripts/run_tests.sh
```

Requires Postgres and Redis (e.g. `docker compose up -d postgres redis`).

## Test layout

| Path | Description |
|------|-------------|
| `tests/unit/` | Unit tests (mock DB; no services) |
| `tests/test_api_cluster_and_retrieval.py` | API validation (cluster by id, retrieval ingest, search/advanced) |
| `tests/test_contract_responses.py` | JSON schema contract (health, status, mood, impacts, universes) |
| `tests/test_auth_and_error_envelope.py` | Auth and error envelope |
| `tests/test_invariants_spec.py` | Ticker whitelist etc. |
| `tests/test_rate_limiting_spec.py` | Rate limit 429 |
| `tests/test_sse_stream.py` | SSE content-type (may skip) |
| `tests/test_ssrf.py` | SSRF guards |
| `tests/test_topics_and_metrics.py` | Topics index, metrics |
| `tests/test_openapi_refs.py` | OpenAPI file and refs |
| `tests/integration/test_advanced_search_pipeline.py` | 2-tier retrieval (mock provider, cache) |
| `tests/integration/test_pipeline_e2e.py` | E2E ingest → cluster (skip unless `SENTIMENT_E2E=1`) |

## New tests (this pack)

- **Unit:** `get_cluster_l3_summary` (mock conn; none, dict, JSON string, invalid, list)
- **Unit:** `RealEmbeddingProvider` timeout/retries config
- **API:** cluster by id invalid/short/404; retrieval ingest empty/missing text/doc_id; search/advanced empty query/body
