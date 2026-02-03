# Full E2E testing

End-to-end tests cover the backend pipeline (ingest → summarize → clusters) and API health/ops, plus the frontend (overview, news, ops page).

## Prerequisites

- **Python 3.11+** (or `uv`)
- **Postgres + Redis** (e.g. `docker compose up -d postgres redis`)
- **Node** (for frontend Playwright)

## Run full E2E

From the repo root:

```bash
./scripts/run_full_e2e.sh
```

This runs:

1. **Backend E2E** (pytest): `SENTIMENT_E2E=1` and `tests/integration/test_pipeline_e2e.py`
   - `test_00_api_health_and_ops_e2e`: GET /v1/health and GET /v1/admin/ops (workers list shape)
   - `test_ingest_summarize_creates_cluster`: one article through ingest → summarize → cluster (LLM/embedding mocked)
2. **Frontend E2E** (Playwright): overview, news, ops page (System Overview, Queue Activity, System Counts)

## Run backend E2E only

```bash
export SENTIMENT_E2E=1
export DATABASE_URL=postgresql://sentiment:sentiment@localhost:5432/sentiment
export REDIS_URL=redis://localhost:6379/0
uv run python -m pytest tests/integration/test_pipeline_e2e.py -v
```

Or with `python3.11` if you don’t use `uv`:

```bash
SENTIMENT_E2E=1 python3.11 -m pytest tests/integration/test_pipeline_e2e.py -v
```

## Run frontend E2E only

```bash
cd frontend
npm run test:e2e
```

Playwright starts the dev server (`npm run dev`) and runs tests against `http://localhost:3000`.

## Markers

Backend E2E tests are marked with `pytest -m e2e`. To run only E2E when other tests exist:

```bash
SENTIMENT_E2E=1 uv run python -m pytest tests/ -m e2e -v
```

(Note: running `tests/ -m e2e` may pull in other modules that need Python 3.11+; running `tests/integration/test_pipeline_e2e.py` directly is recommended.)
