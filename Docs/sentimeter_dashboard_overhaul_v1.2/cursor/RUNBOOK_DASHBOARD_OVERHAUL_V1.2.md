# Dashboard Overhaul Runbook v1.2 (Do This In Order)

1) Apply tokens + glass system
2) Replace shell layout (sidebar/topbar/status pills)
3) Implement API client + Zod contracts + hooks
4) Implement Overview
5) Implement News + Cluster Detail
6) Implement Markets/Sectors/Tickers/Topics/Research/Ops/Sources/Settings
7) Add lint/typecheck/unit tests
8) Add Playwright + screenshots
9) Run all quality gates and save artifacts

Commands:
- cd frontend
- npm i
- npm run lint | tee test-artifacts/lint.txt
- npm run typecheck | tee test-artifacts/typecheck.txt
- npm run test | tee test-artifacts/vitest.txt
- npm run test:e2e
