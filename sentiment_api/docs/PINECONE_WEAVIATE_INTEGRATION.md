# Pinecone or Weaviate integration — what needs to be done

This doc outlines what is required to introduce **Pinecone** or **Weaviate** as the vector store for embeddings (3072-dim, text-embedding-3-large), while keeping Postgres for relational data (clusters, articles, etc.).

## Current state

- **Embeddings** are stored in Postgres (`embeddings` table, pgvector `vector(3072)`).
- **No IVFFlat index** (pgvector limit 2000 dimensions), so similarity search is sequential scan.
- **Write path**: worker embeds articles and clusters → `insert_embedding(conn, object_type, object_id, model, embedding)` in `db/repo.py`.
- **Read path 1 (worker)**: `get_clusters_for_embedding(conn, limit=500, model_id)` loads cluster IDs + vectors from Postgres; then `find_nearest_cluster(embedding, clusters_data)` in Python (cosine similarity).
- **Read path 2 (RAG)**: `retrieve_similar(conn, query_embedding, model_id, top_k)` — SQL `ORDER BY e.embedding <=> $2::vector LIMIT top_k` and join to `clusters` for headline/topics/impact.

## Why Pinecone or Weaviate

- **Indexed similarity search** at 3072 dimensions (no pgvector 2000-dim limit).
- **Scale**: better latency and throughput for large embedding tables.
- **Managed**: no index tuning (IVFFlat lists, HNSW M/ef) on our side.

## What needs to be done

### 1. Config

- Add vector store backend: `pgvector` | `pinecone` | `weaviate` (e.g. `VECTOR_STORE_BACKEND` or in existing settings).
- **Pinecone**: API key, environment (e.g. `us-east-1`), index name. Index must exist with dimension 3072, metric `cosine`.
- **Weaviate**: URL, optional API key, class/schema name. Class with `vectorizer: "none"`, dimension 3072; we provide vectors on upsert.

### 2. Vector store abstraction

- **Interface** (e.g. `sentiment_api/vector_store/base.py`):
  - `upsert(id: str, vector: list[float], metadata: dict) -> None`
  - `search(vector: list[float], top_k: int, filter_metadata: dict | None) -> list[tuple[str, float]]`  (id, score)
  - Optional: `get_many(limit: int, filter_metadata: dict) -> list[tuple[str, list[float]]]` for worker’s “get cluster vectors” (Pinecone/Weaviate can expose list/fetch by metadata filter).
- **Implementations**:
  - **pgvector**: wrap current `insert_embedding` + `get_clusters_for_embedding` / `retrieve_similar` (or keep them in repo and call from adapter).
  - **Pinecone**: use `pinecone` SDK; id = `{object_type}:{object_id}:{model_id}`; metadata = `object_type`, `object_id`, `model_id`; `index.upsert()` and `index.query(vector=..., top_k=..., filter=...)`.
  - **Weaviate**: use `weaviate-client`; class with vector property; object id and metadata; `client.data_object.create()` and `client.query.get().with_near_vector().with_limit()`.

### 3. ID and metadata convention

- **ID**: `{object_type}:{object_id}:{model_id}` (e.g. `cluster:clu_abc:openai:text-embedding-3-large`) so upserts are idempotent and filterable.
- **Metadata** (for filtering): `object_type`, `object_id`, `model_id` so RAG can filter `object_type=cluster` and `model_id=...`; worker can filter `object_type=cluster` for get_many.

### 4. Wire backend into app

- **Repo layer**: `insert_embedding` and `get_clusters_for_embedding` / RAG retrieval call the chosen backend (pgvector, Pinecone, or Weaviate) based on config. Pass `conn` only when backend is pgvector.
- **RAG** (`llm/rag.py`): `retrieve_similar` becomes “vector_store.search(query_embedding, top_k, filter={object_type: 'cluster', model_id})” then load cluster headline/topics/impact from **Postgres** by cluster_id (clusters stay in Postgres).
- **Worker** (`ingest/worker.py`):  
  - **Option A (dual-write)**: keep writing to Postgres; also upsert to Pinecone/Weaviate so RAG uses the external index. `get_clusters_for_embedding` stays on Postgres (no change to worker clustering logic).  
  - **Option B (full migration)**: write only to Pinecone/Weaviate; `get_clusters_for_embedding` reads from external store (e.g. list/fetch with filter object_type=cluster, limit 500). Worker then runs `find_nearest_cluster` on that list as today.

### 5. Index creation (Pinecone / Weaviate)

- **Pinecone**: create index (console or SDK): dimension 3072, metric cosine, optional pod type. Document in README or `docs/`.
- **Weaviate**: create class/schema (vectorizer none, vector dimension 3072). Document or script.

### 6. Dependencies

- Add optional deps: `pinecone-client` and/or `weaviate-client` (or `weaviate-client` with async if needed). Add to `pyproject.toml` under `[project.optional-dependencies]` e.g. `vector-pinecone` and `vector-weaviate`, or as main deps if we ship one as default.

### 7. Backfill / migration

- Script to read existing embeddings from Postgres (`SELECT object_type, object_id, model, embedding FROM embeddings`) and upsert to Pinecone/Weaviate so existing data is searchable in the new store. Run once when switching.

### 8. Environment and deployment

- **Pinecone**: `PINECONE_API_KEY`, `PINECONE_INDEX`, `PINECONE_ENVIRONMENT` (or host). No extra container; API only.
- **Weaviate**: `WEAVIATE_URL`, optional `WEAVIATE_API_KEY`. If self-hosted, add Weaviate to Docker Compose and wire URL; or use Weaviate Cloud.

#### Local Weaviate (implemented)

- **Docker Compose**: Weaviate service is included (`weaviate`). Ports: 8081 (HTTP), 50051 (gRPC). Use `VECTOR_STORE_BACKEND=weaviate` and `WEAVIATE_URL=http://weaviate:8080` (from api/worker containers).
- **Vector dimension**: 3072 (OpenAI `text-embedding-3-large`). Collection is created on first use with self-provided vectors; dimension is inferred from first insert.
- **Env**: `VECTOR_STORE_BACKEND=weaviate`, `WEAVIATE_URL` (default `http://localhost:8080`), optional `WEAVIATE_CLASS` (default `Embedding`).

### 9. Testing

- Unit tests for vector store adapter (mock Pinecone/Weaviate or use pgvector).
- Integration test: upsert a vector, search, assert order/scores (or run against real index in CI if available).

---

## Suggested order of work

1. Add config keys and vector store abstraction (protocol + pgvector implementation).
2. Implement Pinecone (or Weaviate) adapter: upsert + search; optional get_many for worker.
3. Wire config to repo/rag: if backend is pinecone/weaviate, use adapter; else keep current pgvector path.
4. Dual-write in worker (Postgres + Pinecone/Weaviate) and switch RAG to external search; verify RAG and clustering.
5. Document index creation and env vars; add backfill script.
6. (Optional) Later: full migration (worker writes only to external store, get_clusters_for_embedding from external store).

---

## Pinecone vs Weaviate (short)

| | Pinecone | Weaviate |
|---|----------|----------|
| **Hosting** | Managed only (no self-host) | Managed or self-hosted (Docker) |
| **API** | REST / Python SDK, simple upsert/query | REST + GraphQL, richer schema and queries |
| **Filtering** | Metadata filter on query | Filter by class and properties |
| **Setup** | Create index (dim, metric), get API key | Create class (vector dim), optional auth |
| **Fit** | Minimal change: index + upsert + query by vector | Good if you want one stack (e.g. self-hosted Weaviate in Compose) |

Choose **Pinecone** for fastest path (managed, few moving parts); choose **Weaviate** if you prefer self-hosting or want GraphQL/rich schema.
