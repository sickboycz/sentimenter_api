# Frontend testing (starter)

Recommended stack:
- Unit/component: Vitest + React Testing Library
- E2E: Playwright

This scaffold does not include these deps by default.

## Suggested minimal E2E checks
- Overview page loads
- News feed loads
- Impacts page loads
- Ops page loads

## Acceptance criteria
- In CI, run `npm run lint` + `npm run test` + `npm run test:e2e`
