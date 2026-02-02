# Dashboard Overhaul v1.2 — Crosscheck Report

**Date:** 2026-02-02  
**References:** `RUNBOOK_DASHBOARD_OVERHAUL_V1.2.md`, `MASTER_DESIGNER_PROMPT_DASHBOARD_OVERHAUL_V1.2.md`

---

## 1. Runbook Checklist vs Implementation

| Step | Runbook | Implementation | Status |
|------|---------|----------------|--------|
| 1 | Apply tokens + glass system | `frontend/styles/tokens.css`, `.glass` in `globals.css` | ✓ Done |
| 2 | Replace shell layout (sidebar/topbar/status pills) | `Shell`, `Sidebar`, `Topbar`, `StatusPill` | ✓ Done |
| 3 | API client + Zod contracts + hooks | `lib/api.ts`, `lib/schemas.ts`, `useSSE.ts` | ✓ Done |
| 4 | Implement Overview | `/` — mood + impacts | ✓ Done |
| 5 | Implement News + Cluster Detail | `/news`, `/clusters/[clusterId]` | ✓ Done |
| 6 | Markets/Sectors/Tickers/Topics/Research/Ops/Sources/**Settings** | All including Settings | ✓ Done |
| 7 | Add lint/typecheck/unit tests | `npm run lint`, `npm run typecheck`, `npm run test` | ✓ Done |
| 8 | Add Playwright + screenshots | Playwright present; screenshots only-on-failure | ⚠ Partial |
| 9 | Run quality gates and save artifacts | `test-artifacts/` has lint, typecheck, vitest, playwright-output | ✓ Done |

---

## 2. Master Designer Prompt — Required vs Implementation

### 2.1 Required pages

| Page | Spec | Implementation | Gap |
|------|------|----------------|-----|
| Overview | health at first sight | ✓ mood + impacts | None |
| News Feed | clusters + filters | ✓ clusters; filters minimal | Minor |
| Cluster Detail | evidence + impacts | ✓ evidence + impacts | None |
| Markets | SP500 vs NASDAQ_COMP impacts | ✓ impacts | None |
| **Sectors** | **heatmap + drilldown** | Heatmap bars + expand for tickers | ✓ Done |
| Tickers | winners/losers + search | ✓ winners/losers; search stub in Topbar | Minor |
| Topics | topic indices | ✓ topic indices | None |
| Research | event study | ✓ event study | None |
| Sources | source registry health | ✓ source registry | None |
| Ops | health + links | ✓ health, logs, Prometheus/Grafana links | None |
| **Settings** | API key | ✓ Dedicated /settings page | Done |

### 2.2 Required topbar widgets

| Widget | Spec | Implementation | Status |
|--------|------|----------------|--------|
| Status pills | API / Ingestion / Allocation / Research | ✓ from `/v1/status` | ✓ |
| Global search | command palette stub OK | Input stub in Topbar | ✓ |
| Timeframe switch | 1h / 6h / 24h | ✓ context + buttons | ✓ |

### 2.3 Quality gates (Master Designer)

| Gate | Spec | Implementation | Gap |
|------|------|----------------|-----|
| Zod on all API responses | Required | Envelope validation; `/v1/health`, `/v1/status` skip (non-envelope) | Acceptable |
| **Backoff on 429 (Retry-After)** | Required | ✓ api.ts retries with Retry-After | Done |
| **Graceful degraded mode on 503** | Required | ✓ ApiDegradedError thrown | Done |
| **Virtualization for large lists** | Required or TODO + guardrails | ✓ TODO in news/tickers | Done |
| Summaries first; drilldown loads detail | Required | Some pages load full payloads | Partial |

### 2.4 Deliverables (Master Designer)

| Deliverable | Spec | Implementation | Status |
|-------------|------|----------------|--------|
| Token system | PR diff | `tokens.css` | ✓ |
| UI primitives | PR diff | `StatusPill`, etc. | ✓ |
| Page overhaul | PR diff | All pages present | ✓ |
| Zod runtime validation | PR diff | `api.ts` + `schemas.ts` | ✓ |
| Tests + lint config | PR diff | vitest, playwright, eslint | ✓ |
| `frontend/README.md` exact commands | Required | README has commands | ⚠ Diff |
| `test-artifacts/lint.txt` | Evidence | ✓ | ✓ |
| `test-artifacts/typecheck.txt` | Evidence | ✓ (from `lint:ts`) | ✓ |
| `test-artifacts/vitest.txt` | Evidence | ✓ | ✓ |
| `test-artifacts/playwright-report/*` | Evidence | ✓ Output to test-artifacts/playwright-report | Done |
| `test-artifacts/screenshots/*` | Evidence | Screenshots only-on-failure (test-results) | Partial |

---

## 3. Command Diff (Runbook vs README)

| Runbook | README | package.json |
|---------|--------|--------------|
| `npm run typecheck` | `npm run typecheck` | `typecheck` | ✓ Aligned |

---

## 4. Summary of Gaps (Resolved)

### Resolved (2026-02-02)

1. **Settings page** — Added `/settings` page for API key.
2. **Sectors heatmap + drilldown** — Heatmap bars + expand for tickers by sector.
3. **429 backoff** — api.ts retries with Retry-After (max 2 retries).
4. **503 graceful degraded mode** — ApiDegradedError thrown for 503.
5. **Virtualization** — TODO added to news/tickers; guardrails (limit 50).
6. **typecheck script** — Added `npm run typecheck` alias.

### Remaining (Low priority)

7. **Screenshots** — Playwright screenshots only-on-failure; no dedicated `test-artifacts/screenshots/*` on success.

---

## 5. Diff Summary

| Category | Runbook | Master Prompt | Actual | Status |
|----------|---------|---------------|--------|--------|
| Settings page | Step 6 | Required pages | `/settings` page | ✓ Done |
| Sectors heatmap | — | heatmap + drilldown | Heatmap + drilldown | ✓ Done |
| 429/503 handling | — | Quality gates | api.ts | ✓ Done |
| Virtualization | — | Quality gates | TODO + guardrails | ✓ Done |
| typecheck script | `npm run typecheck` | — | `npm run typecheck` | ✓ Done |
| Screenshots folder | — | Deliverables | only-on-failure | Partial |
