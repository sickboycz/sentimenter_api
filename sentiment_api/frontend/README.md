# sentiment-dashboard (frontend)

Next.js dashboard for sentiment_api. Connects to API on port 8080.

## Location in repo
This dashboard lives in:

- `frontend/` (Next.js App Router)
- primary pages: `frontend/app/*`

## Run locally (node)
```bash
cd frontend
npm install
npm run dev
# open http://localhost:3000
```

## Run locally (docker-compose)
From repo root:

```bash
docker compose up --build frontend
# open http://localhost:3000
```

## Configure API base URL
Set:

- `NEXT_PUBLIC_API_BASE_URL`

Examples:

- local: `http://localhost:8000`
- docker: `http://api:8000`

## Quality gates (exact commands)

```bash
cd frontend
npm install
npm run lint | tee test-artifacts/lint.txt
npm run typecheck | tee test-artifacts/typecheck.txt
npm run test | tee test-artifacts/vitest.txt
npm run test:e2e
```

Artifacts are written to `frontend/test-artifacts/`. E2E requires the dev server (Playwright starts it automatically unless `E2E_NO_SERVER=1`).

## Notes
- This UI expects the API endpoints defined in the PRD:
  - `/v1/mood/now`
  - `/v1/impacts/latest`
  - `/v1/news/clusters`
  - `/v1/news/clusters/{cluster_id}`
  - `/v1/health`
