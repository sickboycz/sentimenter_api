# Sentimeter Dashboard Overhaul v2.0 (ZIP package)

This is a **design-first** dashboard overhaul scaffold that aims to match the attached high-end glassy mockups.

## Contents
- `frontend/` — Next.js App Router dashboard
- `docker/` — Dockerfile for frontend
- `docker-compose.frontend.yml` — quick run
- `docs/reference/` — current vs target UI screenshots for comparison
- `cursor/MASTER_PROMPT_UI_OVERHAUL_V2.0.md` — copy/paste prompt for Cursor

## Quick start (demo mode)
```bash
cd frontend
npm install
npm run dev
# open http://localhost:3000
```

Enable demo mode in Settings (or set env `NEXT_PUBLIC_DEMO_MODE=1`).

## Run quality gates
```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

## Docker
```bash
docker compose -f docker-compose.frontend.yml up --build
# open http://localhost:3000
```
