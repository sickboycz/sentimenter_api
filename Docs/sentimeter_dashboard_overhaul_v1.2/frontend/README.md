# Sentimeter Dashboard (Overhaul v1.2)

## Run
```bash
cd frontend
npm install
npm run dev
# http://localhost:3000
```

## Quality gates
```bash
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

## API key
Open `/settings` and paste your `api_key`. Stored in localStorage as `SENTIMETER_API_KEY`.

## API base URL
Set `NEXT_PUBLIC_API_BASE_URL` (default: `http://localhost:8000`).
