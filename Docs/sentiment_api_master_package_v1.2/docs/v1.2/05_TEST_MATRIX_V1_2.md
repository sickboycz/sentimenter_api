# Test matrix — v1.2

## Unit tests
- Schemas validate and reject extra fields (Pydantic extra=forbid)
- Error envelope shape always includes meta + errors
- Sorting and bounds for ticker impacts
- Invariants enforced (no unknown tickers)

## Contract tests
- OpenAPI file parses and references existing JSON schemas
- JSON schemas validate sample fixtures (goldens)

## Integration tests (docker compose)
- DB migrations apply cleanly
- /v1/health returns ok when DB ready
- /metrics returns Prometheus text format
- /api/sp-sentiment returns array of records (compatibility)

## Security tests
- SSRF blocked on fetcher (deny private IPs)
- Prompt injection cannot output unknown tickers (whitelist enforced)

## Performance tests (optional)
- /v1/news/clusters p95 < 300ms for 50 items
- /v1/impacts/latest p95 < 500ms

## Evidence checklist
- CI output showing passing unit/contract tests
- One sample response per endpoint (golden JSON fixtures)
- Grafana screenshot of API request rate and latency
- Calibration ledger example row (predicted vs realized)

## Acceptance criteria
- AC-TST1: `pytest -q` runs successfully for unit + contract tests.
- AC-TST2: Integration tests are runnable via `RUN_INTEGRATION=1`.
