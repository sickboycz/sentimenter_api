# Frontend testing (v1.2)

## Unit tests (Vitest + React Testing Library)

```bash
npm run test
```

Tests: `tests/lib/`, `tests/components/`

## E2E tests (Playwright)

Requires frontend + API running (e.g. `docker compose -f docker-compose.frontend_only.yml up -d`).

```bash
# With Docker stack running on localhost:3000
E2E_NO_SERVER=1 E2E_BASE_URL=http://localhost:3000 npm run test:e2e
```

Tests: `tests/e2e/pages.spec.ts` — Overview, News, Topics, Ops, Sources pages load.

**Note:** Playwright may fail to launch Chromium in some environments (sandbox restrictions). Run in a regular terminal if needed.

## Lint

```bash
npm run lint
```
