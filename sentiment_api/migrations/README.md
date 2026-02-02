# sentiment_api — Database migrations

## Order (from zero to full)

Apply in this order on an **empty** database:

| Order | File | Purpose |
|-------|------|---------|
| 1 | `00_base_schema.sql` | Base schema: enums, sources, articles, clusters, events, embeddings, runs, etc. |
| 2 | `v1.1_add_universes.sql` | Universes, sectors, securities, universe_memberships (idempotent: IF NOT EXISTS) |
| 3 | `v1.1_asset_targeting_audit.sql` | cluster_asset_targeting_audit table (idempotent) |
| 4 | `v1.1_retention_tombstone.sql` | deleted_at on articles for retention (idempotent) |

All scripts are **safe to re-run** (CREATE IF NOT EXISTS, ADD VALUE IF NOT EXISTS, etc.).

## Apply from zero (one command)

From `sentiment_api/` with Postgres running (Docker or local):

```bash
./scripts/apply_schema_from_zero.sh
```

Or manually with Docker Compose:

```bash
cd /path/to/sentiment_api
for f in migrations/00_base_schema.sql migrations/v1.1_add_universes.sql migrations/v1.1_asset_targeting_audit.sql migrations/v1.1_retention_tombstone.sql; do
  docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres \
    psql -U sentiment -d sentiment -f - < "$f"
done
```

## Why we can't use 3072 dimensions with IVFFlat

We use **OpenAI text-embedding-3-large**, which produces **3072-dimensional** vectors. The `embeddings` table stores these in a `vector(3072)` column (pgvector).

**pgvector's IVFFlat index has a hard limit of 2000 dimensions.** This limit is defined in the pgvector source (`IVFFLAT_MAX_DIM`). If you create an IVFFlat index on a column with more than 2000 dimensions, Postgres raises:

```text
ERROR: column cannot have more than 2000 dimensions for ivfflat index
```

So we **do not create** an IVFFlat index on `embeddings.embedding`. Implications:

- **Similarity search** (e.g. cosine distance over embeddings) uses a **sequential scan** over the table. For small or medium-sized tables (thousands to low hundreds of thousands of rows) this is acceptable. For very large tables, latency will grow.
- **Lookups by (object_type, object_id)** use the existing btree index `idx_embeddings_object`, so they remain fast.

**Options if you need faster similarity search at scale:**

1. **Use a smaller embedding model** that outputs ≤2000 dimensions (e.g. 1536 or 1024), then you can create an IVFFlat (or HNSW) index on that column.
2. **Wait for pgvector** to support higher dimensions for IVFFlat/HNSW (or use a fork that raises the limit).
3. **Dimensionality reduction** (e.g. PCA) to reduce 3072 → 2000 before storing and indexing (with a trade-off in recall).
4. **External vector store** (e.g. Pinecone, Weaviate) that supports >2000 dimensions for indexed search. See `docs/PINECONE_WEAVIATE_INTEGRATION.md`. When using Weaviate, the 2-tier retrieval pipeline (see `docs/RETRIEVAL_TWOTIER.md`) uses a **SQLite embedding cache** for tier-B vectors; no PostgreSQL migration is required for that cache.

Until then, we keep `vector(3072)` and rely on sequential scan for similarity queries and on `idx_embeddings_object` for direct lookups.

## Reserved keywords

- **`outcomes."window"`** — In PostgreSQL, `window` is a reserved keyword (window functions). The column is therefore defined and referenced as `"window"` in SQL. The application (e.g. `sentiment_api/engines/outcomes.py`) uses `"window"` in INSERT/ON CONFLICT.
