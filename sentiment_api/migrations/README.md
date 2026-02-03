# sentiment_api — Database migrations

## Order (from zero to full)

Apply in this order on an **empty** database:

| Order | File | Purpose |
|-------|------|---------|
| 1 | `00_base_schema.sql` | Base schema: enums, sources, articles, clusters, events, embeddings, runs, etc. |
| 2 | `v1.1_add_universes.sql` | Universes, sectors, securities, universe_memberships (idempotent: IF NOT EXISTS) |
| 2b | `v1.1_add_industries.sql` | Industries table (GICS industries under sectors; idempotent) |
| 3 | `v1.1_asset_targeting_audit.sql` | cluster_asset_targeting_audit table (idempotent) |
| 4 | `v1.1_retention_tombstone.sql` | deleted_at on articles for retention (idempotent) |
| 5 | `v1.2_embedding_dim_768.sql` | Drops and recreates embeddings with vector(768) (for DBs created with 3072) |

All scripts are **safe to re-run** (CREATE IF NOT EXISTS, etc.). After changing to 768 dim, **restart DB** (e.g. `./scripts/reset_db_fresh.sh`) then run seeding so embeddings are 768-dim.

## Full fresh start (no debugging)

To remove the current Docker build, rebuild without the debug overlay, migrate DB, and seed:

```bash
./scripts/fresh_start_production.sh
```

This runs: `down --volumes`, `build --no-cache`, `up postgres redis api`, then `reset_db_fresh.sh` (migrate + seed), then `up` (all services). Use `--keep-data` to keep postgres/redis volumes; use `--production` to add `docker-compose.production.yml`.

## Apply from zero (one command)

From `sentiment_api/` with Postgres running (Docker or local):

```bash
./scripts/apply_schema_from_zero.sh
```

## Reset DB to fresh install (keep sources, nasdaq, sectors)

Drops all tables, reapplies migrations, then re-seeds universes (sectors, industries, S&P 500, Nasdaq-100) from `artifacts/*.csv` or `registry/*.csv` (artifacts are in git and used when registry has no CSVs). Does **not** change `source_registry.yaml` or registry files.

From `sentiment_api/` with Postgres and API containers up:

```bash
./scripts/reset_db_fresh.sh
```

Or manually with Docker Compose:

```bash
cd /path/to/sentiment_api
for f in migrations/00_base_schema.sql migrations/v1.1_add_universes.sql migrations/v1.1_add_industries.sql migrations/v1.1_asset_targeting_audit.sql migrations/v1.1_retention_tombstone.sql; do
  docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres \
    psql -U sentiment -d sentiment -f - < "$f"
done
```

## Embedding dimensions (Tier A 384, Tier B 768)

We use **OpenAI text-embedding-3-small** with **Tier A = 384 dim** and **Tier B = 768 dim**. The `embeddings` table stores **768-dimensional** vectors (`vector(768)`). Clustering and DB use Tier B (768). With 768 dimensions, pgvector **can** use IVFFlat/HNSW indexes if you add them later (768 &lt; 2000).

## Reserved keywords

- **`outcomes."window"`** — In PostgreSQL, `window` is a reserved keyword (window functions). The column is therefore defined and referenced as `"window"` in SQL. The application (e.g. `sentiment_api/engines/outcomes.py`) uses `"window"` in INSERT/ON CONFLICT.
