# Missing Files — Main Repo vs v1.2 Package

**Date:** 2026-02-02  
**Reference:** `Docs/sentiment_api_master_package_v1.2`  
**Purpose:** Document files present in v1.2 package but not in main repo, with reasons why each is not implemented.

---

## 1) Executive Summary

The v1.2 package is a **skeleton/scaffold** with a different architecture (backend scaffold, separate docker layout). The main repo uses a **unified sentiment_api package** and evolved from v1.1 tech package. Most “missing” files are either:

- **Architectural difference** — v1.2 has `backend/` scaffold; main has `sentiment_api/` package (equivalent functionality)
- **Different placement** — docs, registry, schemas live under `Docs/` or v1.1 package
- **Intentional omission** — migration runner, .env.example, cursor prompt (reference-only)
- **Not yet added** — frontend tests scaffold, v1.2 registry loader

---

## 2) Missing Files — Detailed

### 2.1 Root / Config

| File (v1.2) | In Main Repo | Why Not Implemented |
|-------------|--------------|----------------------|
| `.env.example` | ❌ | Main uses pydantic-settings with defaults; env vars documented in README. v1.2 .env.example targets its backend layout (DATABASE_URL, OTEL). Could be added for consistency. |

### 2.2 `cursor/`

| File (v1.2) | In Main Repo | Why Not Implemented |
|-------------|--------------|----------------------|
| `cursor/MASTER_PROMPT.md` | ❌ | Reference prompt for Cursor IDE. Lives in `Docs/sentiment_api_master_package_v1.2/cursor/` as source of truth. Main repo does not duplicate—it consumes the package. |

### 2.3 `docs/`

| Path (v1.2) | In Main Repo | Why Not Implemented |
|-------------|--------------|----------------------|
| `docs/00_INDEX.md` | ❌ | Docs live at `Docs/` (parent). v1.2 docs are inside the package; main repo keeps specs in `Docs/sentiment_api_master_package_v1.2/docs/` and `Docs/sentiment_api_tech_package_v1.1/`. |
| `docs/original/*` | ❌ | Same—specs are in parent `Docs/` tree. |
| `docs/v1.2/*` | ❌ | Same. Main repo references `Docs/sentiment_api_master_package_v1.2` as source of truth. |

### 2.4 `backend/` (entire scaffold)

| Path (v1.2) | In Main Repo | Why Not Implemented |
|-------------|--------------|----------------------|
| `backend/app/*` | Different layout | v1.2 uses `backend/app/` (FastAPI scaffold). Main uses `sentiment_api/` package with `api/`, `db/`, `engines/`, etc. Functionally equivalent; architecture differs. |
| `backend/app/db/engine.py` | ❌ | v1.2 uses SQLAlchemy; main uses asyncpg directly (`sentiment_api/db/pool.py`). |
| `backend/app/deps.py` | ❌ | Main has `sentiment_api/api/auth.py`, `keys.py` for auth. |
| `backend/app/errors/*` | ❌ | Main has `sentiment_api/api/responses.py` and HTTP exception handler in `main.py`. |
| `backend/app/schemas/*` | ❌ | Main returns raw dicts; contract tests validate against JSON schemas. Pydantic schemas not used. |
| `backend/app/utils/request_id.py`, `time.py` | ❌ | Main implements request_id in middleware; time helpers inline. |
| `backend/app/validation/invariants.md` | ❌ | Invariants enforced in code (e.g. ticker whitelist); no separate doc. |
| `backend/db/migrate.py` | ❌ | Main uses `scripts/init_db.sh` + `psql -f schema.sql`. No Python migration runner; schema applied manually. |
| `backend/db/migrations/2026_02_02_0001_base_schema.sql` | Different | Main uses `Docs/sentiment_api_tech_package_v1.1/db/schema.sql` + `migrations/v1.1_*`. v1.2 migrations not adopted. |
| `backend/db/migrations/2026_02_02_0002_add_impacts_and_topics.sql` | Different | Main has `migrations/v1.1_asset_targeting_audit.sql`, etc. Different migration set. |
| `backend/db/schema/v1_1_schema.sql`, `v1_2_tables.sql` | Different | Main uses v1.1 schema from tech package; v1.2 tables not applied. |
| `backend/mypy.ini`, `ruff.toml` | ❌ | Main has pyproject.toml; no mypy/ruff config. |
| `backend/requirements.txt`, `requirements-dev.txt` | ❌ | Main uses `pyproject.toml` + `uv`. |

### 2.5 `docker/`

| File (v1.2) | In Main Repo | Why Not Implemented |
|-------------|--------------|----------------------|
| `docker/api/Dockerfile` | ❌ | Main uses root `Dockerfile` for API. Single Dockerfile at repo root. |
| `docker/migrate/Dockerfile` | ❌ | Main has no migrate container; schema applied via `scripts/init_db.sh` + psql. v1.2 uses separate migrate service. |
| `docker/frontend/Dockerfile` | ✓ | Main has `docker/frontend/Dockerfile`. |

### 2.6 `registry/`

| File (v1.2) | In Main Repo | Why Not Implemented |
|-------------|--------------|----------------------|
| `registry/sources.yaml` | ❌ | Main uses `Docs/sentiment_api_tech_package_v1.1/registry/source_registry.yaml` (v1.1 format). v1.2 `sources.yaml` has packs + different structure. Loader not adapted. |
| `registry/sources.schema.json` | ❌ | v1.2 registry schema; main validates against v1.1 `source_registry.schema.json`. |

### 2.7 `openapi/`

| File (v1.2) | In Main Repo | Why Not Implemented |
|-------------|--------------|----------------------|
| `openapi/sentiment_api.openapi.v1.1.yaml` | ❌ | Main has `openapi/sentiment_api.openapi.v1.2.yaml` only. v1.1 YAML kept only in package for reference. |
| `openapi/schemas/*` | ✓ (at `schemas/`) | Main has `schemas/` at repo root (copied from v1.2). |

### 2.8 `frontend/`

| Path (v1.2) | In Main Repo | Why Not Implemented |
|-------------|--------------|----------------------|
| `frontend/tests/README.md` | ❌ | v1.2 suggests Vitest + Playwright. Main frontend has no tests/ folder. Testing scaffold not added. |
| `frontend/tests/*` (actual tests) | ❌ | No frontend unit/e2e tests in main. |

### 2.9 `infra/`

| File (v1.2) | In Main Repo | Why Not Implemented |
|-------------|--------------|----------------------|
| `infra/docker-compose.observability.yml` | — | Removed; observability stack is in main `docker-compose.yml`. |

---

## 3) Summary by Reason

| Reason | Count | Examples |
|--------|-------|----------|
| Architectural difference (backend vs sentiment_api) | ~25 | backend/app/*, backend/db/* |
| Different placement (Docs, registry, schemas) | ~15 | docs/, registry/, openapi layout |
| Intentional omission (reference/skeleton) | ~5 | cursor/MASTER_PROMPT.md, .env.example |
| Not yet added | ~3 | frontend/tests/, migrate container, v1.2 registry loader |
| Implemented elsewhere | ~10 | request_id, errors, auth, Dockerfile |

---

## 4) Recommendations (Implemented 2026-02-02)

1. ✓ **`.env.example`** — Added; documents SENTIMENT_API_*, DATABASE_URL, REDIS_URL, OPENAI_API_KEY.
2. ✓ **`frontend/tests/`** — Added README; Vitest/Playwright scaffold when tests are prioritized.
3. ⚠ **`docker/migrate/`** — Optional; main uses scripts/init_db.sh.
4. ⚠ **`registry/sources.yaml`** — Keep v1.1; v1.2 loader optional.
5. ✓ **`cursor/MASTER_PROMPT.md`** — Keep in v1.2 package.

## 5) Health Monitoring (Implemented 2026-02-02)

- **Prometheus** — Scrapes api:8080/metrics; job=sentiment_api.
- **Grafana** — Dashboards: sentiment_api overview, Health Monitoring (API up, request rate, latency, errors, queue depth, ingestion lag).
- **Restart matrix** — docs/RESTART_MATRIX.md (restart policies, health checks, health gates).
- **Observability runbook** — docs/OBSERVABILITY_RUNBOOK.md.
- **API healthcheck** — GET /v1/health; start_period 10s.
- **Worker/Daemon healthcheck** — Redis ping.
