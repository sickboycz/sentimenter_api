# sentiment-dashboard (frontend)

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

## Notes
- This UI expects the API endpoints defined in the PRD:
  - `/v1/mood/now`
  - `/v1/impact/summary`
  - `/v1/news/clusters`
  - `/v1/news/clusters/{cluster_id}`
  - `/v1/health`
