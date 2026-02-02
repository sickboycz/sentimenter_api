# MASTER DESIGNER PROMPT (Cursor / Codex) — Sentimeter Dashboard Overhaul v1.2

You are implementing a **top-tier, glassy, professional, not-overdone** dashboard UI for Sentimeter (sentiment_api).
Use the attached reference images as the aesthetic target: dark glass, subtle gradients, precise spacing, “health at first sight,” no clutter.

## Hard constraints
- Use ONLY endpoints present in `openapi/sentiment_api.openapi.v1.2.yaml` (or the latest OpenAPI file in repo).
- UI is analysis/monitoring only. No trading actions.
- Deterministic rendering and deterministic sorting. No random UI states.
- Runtime response validation (Zod) on all API responses.
- All changes must include: lint, typecheck, unit tests, E2E (Playwright), and validation artifacts.
- Every container has a health endpoint; Prometheus + Grafana are wired; Ops page links to them.

## Required pages
- Overview (health at first sight)
- News Feed (clusters + filters)
- Cluster Detail (evidence + impacts)
- Markets (SP500 vs NASDAQ_COMP impacts)
- Sectors (heatmap + drilldown)
- Tickers (winners/losers + search)
- Topics (topic indices)
- Research (event study)
- Sources (source registry health)
- Ops (health + links)
- Settings (API key)

## Required topbar widgets
- Status pills: API / Ingestion / Allocation / Research
- Global search (command palette stub OK)
- Timeframe switch (1h / 6h / 24h)

## Quality gates
- Zod contract validation for all API responses.
- Backoff on 429 (Retry-After).
- Graceful degraded mode on 503.
- Virtualization for large lists (or clear TODO + guardrails).
- Ensure UI does not freeze on large payloads: request summaries first; drilldown loads detail.

## Execution (capture outputs)
Backend (if present):
- `pytest -q` (or your backend test command)
- `python -m backend.db.migrate` (if migration test exists)

Frontend:
- `cd frontend`
- `npm install`
- `npm run lint | tee test-artifacts/lint.txt`
- `npm run typecheck | tee test-artifacts/typecheck.txt`
- `npm run test | tee test-artifacts/vitest.txt`
- `npm run test:e2e`

Stop only when everything is green and screenshots are generated.

## Deliverables
1) PR diff includes:
   - token system
   - UI primitives
   - page overhaul
   - Zod runtime validation
   - tests + lint config
2) `frontend/README.md` contains exact commands
3) Evidence artifacts:
   - `frontend/test-artifacts/lint.txt`
   - `frontend/test-artifacts/typecheck.txt`
   - `frontend/test-artifacts/vitest.txt`
   - `frontend/test-artifacts/playwright-report/*`
   - `frontend/test-artifacts/screenshots/*`

## STOP CONDITION REPORT
When done, output a short report:
- files changed
- commands executed
- test results
- screenshots generated
- any remaining TODOs (must be minimal and non-blocking)
