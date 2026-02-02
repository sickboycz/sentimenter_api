# sentiment_api validation

## Run validation

```bash
cd sentiment_api
./scripts/validation/run.sh
```

**Exit 0** = all checks pass  
**Exit 1** = at least one check failed

## Checks

1. **Pytest** — unit + contract tests (excludes test_sse_stream)
2. **OpenAPI schema** — openapi/sentiment_api.openapi.v1.2.yaml exists
3. **Required files** — schemas, infra configs, docker-compose
4. **Docker Compose** — config validates (base + production)
5. **Deployment scripts** — install.sh, update.sh, rollback.sh exist and executable

## Options

- `--skip-docker` — skip production compose config (e.g. when /srv/sentimenter not present)

## Full validation document

See **docs/VALIDATION_CHECKLIST.md** for manual verification steps and API contract details.
