# sentiment_api — Master Package v1.2

Date: 2026-02-02 (America/Chicago)

This ZIP is a **single consolidated package** that contains:

- All provided v1.0/v1.1 specs and templates
- v1.2 improvement plan (modernization + harmonization + testing + observability + frontend)
- Full OpenAPI + JSON Schema registry (v1.1 baseline + v1.2 deltas)
- Backend & frontend scaffolds
- Observability stack (Prometheus, Grafana, Loki, Tempo)
- Test suite templates (contracts, validation, error model, invariants, rate limiting, SSE)

## Quick start (dev)

### 1) Read the docs (source of truth)
- `docs/00_INDEX.md`
- `docs/original/*` (v1.0/v1.1 master specs)
- `docs/v1.2/*` (what to implement now)

### 2) Run local stack (skeleton)
```bash
docker compose up --build
```

### 3) Run tests
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

## Canonical folders

- `docs/` — specs (contract truth)
- `registry/` — source registry templates
- `openapi/` — OpenAPI + JSON schemas
- `backend/` — FastAPI scaffold + DB migrations + tests
- `frontend/` — Next.js dashboard scaffold
- `infra/` — observability config
- `docker/` — Dockerfiles

## Cursor

Use `cursor/MASTER_PROMPT.md` as the **single prompt** to implement everything and keep strict alignment.
