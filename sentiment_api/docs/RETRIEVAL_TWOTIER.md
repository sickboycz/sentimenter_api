# 2-Tier Retrieval Pipeline (Weaviate “Brain”)

## Why we do this

- **Tier A (cheap, scalable):** Store all chunks as 384- or 768-dim dense vectors in Weaviate plus BM25/keyword fields. This keeps storage and index cost low and allows fast hybrid (vector + BM25) candidate retrieval over the full corpus.
- **Tier B (precise, on demand):** At query time, re-embed only the top-K candidates (e.g. 200) with a higher-dim model (e.g. 768 or 3072) and rerank. We do **not** store Tier B vectors in Weaviate; they are computed on the fly and cached in SQLite by `(model_id, text_hash)`.
- **Result:** You get “big-model” semantic precision only where it matters (top candidates), without storing 3072-dim vectors for every chunk.

## Design overview

1. **Ingest**
   - Chunk documents (news/articles).
   - Compute Tier A embeddings (384 or 768 dim).
   - Store in Weaviate: `vector_a` (default embedding), `text`, and metadata: `doc_id`, `source`, `url`, `published_at`, `tickers`, `sector`, `language`, `text_hash`, `chunk_id`. BM25 runs on the `text` field by default.

2. **Query**
   - **Q1 – Candidate retrieval (cheap):** Hybrid in Weaviate (vector search with Tier A query embedding + BM25 on text). Filters: time range, tickers, source, language. Return top-N candidates (e.g. 200).
   - **Q2 – Tier B rerank (expensive but small):** Re-embed query with Tier B model; for each candidate get Tier B vector from cache or embed (batch); compute cosine similarity and combine with Tier A/BM25 weights.
   - **Q3 (optional):** Cross-encoder rerank for top M (e.g. 20): score(query, doc_text) and fold into final (no-op by default; plug real model when available).

3. **Outputs**
   - Ranked results with `tierA_score`, `bm25_score`, `tierB_score`, optional `cross_score`, `final_score`, and score breakdown.
   - Full trace: `trace_id`, latencies per step, cache hit/miss, candidate count, filter summary, model versions.

## Config knobs

| Variable | Default | Description |
|--------|---------|-------------|
| `RETRIEVAL_TIERA_MODEL_ID` | `openai:text-embedding-3-small:384` | Tier A embedding model (384 or 768 dim). |
| `RETRIEVAL_TIERB_MODEL_ID` | `openai:text-embedding-3-small:768` | Tier B rerank model (768 or 3072 dim for large). |
| `RETRIEVAL_TOPN` | `200` | Number of candidates from hybrid search (Q1). |
| `RETRIEVAL_RERANKN` | `80` | Number of results after Tier B rerank (Q2). |
| `RETRIEVAL_ALPHA` | `0.5` | Hybrid weight: 0 = BM25 only, 1 = vector only. |
| `RETRIEVAL_WEIGHTS` | `{"tierA":0.2,"bm25":0.2,"tierB":0.6,"cross":0.0}` | Final score = wA×tierA + wBM25×bm25 + wB×tierB + wCross×cross. |
| `EMBEDDING_CACHE_PATH` | `/var/lib/sentiment_api/embedding_cache.sqlite` | SQLite path for Tier B vector cache. |
| `WEAVIATE_CHUNK_CLASS` | `RetrievalChunk` | Weaviate collection name for chunk retrieval. |
| `RETRIEVAL_CROSS_TOP_M` | `20` | Run cross-encoder on top M results (0=disabled). |
| `RETRIEVAL_EMBEDDING_TIMEOUT_SEC` | `30.0` | Timeout for embedding provider calls. |
| `RETRIEVAL_EMBEDDING_RETRIES` | `2` | Retries for embedding provider on failure. |

## Operational costs

- **Storage:** Only Tier A vectors (384/768 dim) and text in Weaviate. Tier B vectors are not stored in Weaviate.
- **Compute:** Tier B embeddings and cosine rerank only for top-N candidates per query; batch `embed_docs` reduces API calls.
- **Cache:** SQLite cache keyed by `(model_id, text_hash)` reduces repeat Tier B embeddings for the same chunk text (e.g. second run >80% cache hits in tests).

## How to tune alpha / topN / rerankN

- **alpha:** Higher (e.g. 0.7) favors vector similarity; lower (e.g. 0.3) favors BM25. Use 0.5 for balanced.
- **topN:** Larger (e.g. 300) improves recall for Tier B rerank but increases latency and embedding cost. 200 is a good default.
- **rerankN:** Number of results returned after Tier B. Keep ≤ topN; 80 is usually enough for API responses.

## API

- **POST /v1/search/advanced**
  - Body: `query` (required), `filters` (optional), `topN`, `rerankN`, `alpha`, `weights`.
  - Response: `results[]` with `chunk_id`, `doc_id`, `snippet`, `score_breakdown` (tierA, bm25, tierB, cross, final), `metadata`; and `trace` (trace_id, candidate_count, rerank_count, cache_hit_count, cache_miss_count, latencies, model_tiera, model_tierb).

## Example response (score breakdown)

```json
{
  "meta": { "version": "1.0" },
  "data": {
    "results": [
      {
        "chunk_id": "chunk_1",
        "doc_id": "doc1",
        "snippet": "First chunk about markets...",
        "score_breakdown": {
          "tierA": 0.85,
          "bm25": 0.5,
          "tierB": 0.92,
          "cross": 0.0,
          "final": 0.78
        },
        "metadata": {}
      }
    ],
    "trace": {
      "trace_id": "tr_a1b2c3d4e5f6",
      "candidate_count": 200,
      "rerank_count": 80,
      "cache_hit_count": 120,
      "cache_miss_count": 80,
      "latency_tiera_ms": 45.2,
      "latency_tierb_ms": 312.1,
      "latency_cross_ms": 0.0,
      "filter_summary": {},
      "model_tiera": "openai:text-embedding-3-small:384",
      "model_tierb": "openai:text-embedding-3-small:768"
    }
  },
  "errors": []
}
```

## Sample log lines (trace_id + timings)

```
advanced_search trace_id=tr_a1b2c3d4e5f6 candidate_count=200 rerank_count=80 cache_hits=120 cache_misses=80 tiera_ms=45.20 tierb_ms=312.10
tiera_retrieval trace_id=tr_a1b2c3d4e5f6 candidate_count=200 latency_ms=45.20 filter_summary={}
tierb_rerank trace_id=tr_a1b2c3d4e5f6 rerank_count=80 cache_hits=120 cache_misses=80 latency_ms=312.10
```

## Filters (applied before reranking)

- **sources:** Source allowlist (first source used for Weaviate filter).
- **language:** Language code (e.g. `en`).
- **published_after** / **published_before:** ISO date strings for time range on `published_at`.
- **tickers:** Optional; filters chunks whose `tickers` text contains the given ticker (substring match).

## Ingest (chunk → Weaviate)

- **POST /v1/retrieval/ingest** — Chunk documents and ingest into Weaviate RetrievalChunk (Tier A vectors + text for BM25).
- Body: `{ "documents": [ { "text", "doc_id", "source?", "url?", "published_at?", "tickers?", "sector?", "language?" } ], "max_chars?", "overlap_chars?" }`.
- Chunking: `chunk_text(text, max_chars=512, overlap_chars=64)`; each chunk is embedded with Tier A and upserted with metadata.

## Implementation notes

- Tier B vectors are **never** persisted to Weaviate.
- Cache uses normalized text hash (strip, collapse whitespace) and float32 blob storage.
- Batch embedding for cache misses reduces provider API calls.
- All stages are instrumented: wall-clock timings, cache hit/miss, candidate counts, model IDs.
