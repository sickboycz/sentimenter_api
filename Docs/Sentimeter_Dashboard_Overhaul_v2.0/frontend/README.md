# Sentimeter Dashboard — Overhaul v2.0

This is a **design-first** scaffold that matches the target glassy dashboard references:
- dense but readable information layout
- charts + tables + heatmaps
- health at first sight
- demo mode for offline dev/tests

## Run (dev)
```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

## Configure API base URL
Set env:
- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`

## Demo mode (recommended for first run)
- In Settings, enable Demo mode (or set env `NEXT_PUBLIC_DEMO_MODE=1`).
- Playwright runs in demo mode by default.

## Quality gates
```bash
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

Artifacts:
- `test-artifacts/screenshots/*`
- `test-artifacts/playwright-report/*`
