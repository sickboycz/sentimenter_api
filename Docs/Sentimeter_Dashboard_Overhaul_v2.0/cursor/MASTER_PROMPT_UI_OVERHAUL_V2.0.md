# Cursor Master Prompt — Sentimeter UI Overhaul v2.0 (Design + Implementation)

You are a world-class UI engineer and designer. Your job is to take the existing Sentimeter dashboard and make it match the **attached target mockups**:
- dark glass UI, subtle gradients, sharp hierarchy
- dense information without clutter
- health at first sight
- charts, tables, heatmaps, winners/losers, event feed

## Scope
- Frontend only (Next.js App Router).
- No backend refactors. If an endpoint is missing, add minimal compatible stub and update OpenAPI + tests.

## Hard rules
- All API responses must be runtime-validated (Zod). On mismatch: show degraded UI state (not blank).
- When API returns empty data, show “empty state” + optionally demo fixtures (toggle).
- Implement quality gates: lint, typecheck, unit tests, Playwright screenshots.
- Preserve glass style and layout fidelity.

## Reference images
Use these as visual targets:
- `docs/reference/target_mockup_*.png`
And compare against current implementation screenshots:
- `docs/reference/current_impl_*.png`

## Tasks (execute in order, no questions)
1) Replace existing frontend with the provided v2.0 scaffold under `frontend/`.
2) Ensure routes/pages compile and render.
3) Wire live API calls:
   - `NEXT_PUBLIC_API_BASE_URL`
   - api_key in query param or header
4) Validate all called endpoints exist in OpenAPI. If missing, implement minimal stubs.
5) Run:
   - `npm i`
   - `npm run lint`
   - `npm run typecheck`
   - `npm run test`
   - `npm run test:e2e`
6) Save artifacts:
   - `frontend/test-artifacts/lint.txt`
   - `frontend/test-artifacts/typecheck.txt`
   - `frontend/test-artifacts/vitest.txt`
   - `frontend/test-artifacts/screenshots/*.png`
   - `frontend/test-artifacts/playwright-report/*`

## Acceptance criteria
- Overview shows: gauge, line chart, market impacts, sector table, sector heatmap, winners/losers, clusters grid — even in demo mode.
- News page shows cluster cards with winners/losers preview.
- Cluster detail shows evidence + impacts.
- Ops page shows health, does not look unfinished.
- All quality gate commands pass.
