# Sectors & Industries (registry CSVs)

## File formats

### sectors.csv
- Format: `;Sector Name;Count;Market Cap;Div Yield;P/E;...`
- 11 GICS sectors: Healthcare, Financials, Technology, Industrials, Consumer Discretionary, Materials, Communication Services, Real Estate, Consumer Staples, Energy, Utilities
- Seeded at API startup and during `refresh_universes`
- sector_id = snake_case slug (e.g. `health_care`, `information_technology`)

### industries.csv
- Format: `Industry Name;Count;Market Cap;Div Yield;P/E;...`
- 123 industries (Biotechnology, Banks - Regional, Software - Application, etc.)
- Seeded at API startup and during `refresh_universes` (requires `industries` table)
- industry_id = snake_case slug of name
- sector_id = inferred from industry name using GICS-like keyword rules

## Applying migrations

Before industries are seeded, apply the industries migration:

```bash
cd sentiment_api
# Via apply_schema_from_zero.sh (includes v1.1_add_industries.sql)
./scripts/apply_schema_from_zero.sh

# Or manually if schema already applied:
docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres \
  psql -U sentiment -d sentiment -f - < migrations/v1.1_add_industries.sql
```

## Seeding

- **sectors**: Loaded from `registry/sectors.csv` if present; else hardcoded GICS_11
- **industries**: Loaded from `registry/industries.csv` if present and `industries` table exists

Seeding runs automatically on:
- API startup (lifespan)
- `python -m sentiment_api.universe.refresh` (or `uv run python -m sentiment_api.universe.refresh`)
