# 2-Tier Retrieval Pipeline

This document describes the **2-tier retrieval** design: cheap Tier A (hybrid vector + BM25) candidate retrieval, then on-the-fly Tier B (high-dim) rerank with a SQLite embedding cache. Tier B vectors are **not** stored in Weaviate.

## Why 2-Tier

- **Tier A (384/768 dim)**: Store all chunks with a small embedding + BM25 text. Cheap, scalable hybrid retrieval returns top-N candidates (e.g. 200).
- **Tier B (768 dim)**: Re-embed only the query and those candidates with a large model at query time. Expensive but over a small set; cache candidate vectors by `(model_id, text_hash)` so repeated candidates don’t re-embed.
- **Result**: Tier B 768-dim; “big-model” semantic precision only where it matters (top candidates).

## Design Overview

1. **Ingest**
   - Chunk documents (news/articles).
   - Compute Tier A embeddings (dim 384 or 768).
   - Store in Weaviate collection `RetrievalChunk`: `vector_a`, `text` (BM25), metadata (doc_id, source, url, published_at, tickers, sector, language, text_hash).

2. **Query**
   - **Q1 – Candidate retrieval (cheap)**  
     Hybrid in Weaviate: vector search (Tier A query embedding) + BM25 on text, filters (time, tickers, source, language). Return top-N (e.g. 200).
   - **Q2 – Tier B rerank (expensive, small set)**  
     Re-embed query with Tier B (768). For each candidate: get Tier B vector from cache (`model_id`, `text_hash`) or embed and cache. Cosine similarity with query Tier B vector. Combine with configurable weights (tierA, bm25, tierB, cross). Return top rerank_n (e.g. 80).
   - **Q3 (optional)**  
     Cross-encoder rerank on final M (e.g. 20) – not implemented in initial version.

3. **Outputs**
   - Ranked results with `score_breakdown`: tierA, bm25, tierB, cross, final.
   - Trace: trace_id, latencies per step, cache hit/miss, candidate count, filter summary, model versions.

## Config (add to env / config system)

| Variable | Default | Description |
|----------|---------|-------------|
| `RETRIEVAL_TIERA_MODEL_ID` | `openai:text-embedding-3-small` | Tier A embedding (384/768 dim). |
| `RETRIEVAL_TIERB_MODEL_ID` | `openai:text-embedding-3-small:768` | Tier B rerank (768 dim). |
| `RETRIEVAL_TOPN` | 200 | Candidate count from hybrid search. |
| `RETRIEVAL_RERANKN` | 80 | Top-N after Tier B rerank. |
| `RETRIEVAL_ALPHA` | 0.5 | Hybrid weight: 0 = BM25 only, 1 = vector only. |
| `RETRIEVAL_WEIGHTS` | `{"tierA":0.2,"bm25":0.2,"tierB":0.6,"cross":0.0}` | JSON weights for final score. |
| `EMBEDDING_CACHE_PATH` | `/var/lib/sentiment_api/embedding_cache.sqlite` | SQLite path for Tier B cache. |
| `WEAVIATE_CHUNK_CLASS` | `RetrievalChunk` | Weaviate collection for chunks. |

## API

- **POST /v1/search/advanced**
  - Body: `query` (required), `filters`, `topN`, `rerankN`, `alpha`, `weights` (JSON).
  - Response: `data.results[]` with `chunk_id`, `doc_id`, `snippet`, `score_breakdown`, `metadata`; `data.trace` with trace_id, latencies, cache stats, candidate counts.

## Implementation Notes

- Tier B vectors are **not** stored in Weaviate; only Tier A vectors and text (BM25) are.
- Cache: SQLite table `embedding_cache(model_id, text_hash, dim, vector BLOB, created_at)`. Vector as float32 bytes.
- Text hash: `sha256(normalized_text)`; normalize = strip + collapse whitespace.
- Filters (time range, tickers, source, language) are applied in Weaviate at Q1, before rerank.
- Logging: structured logs with trace_id, candidate_count, cache_hit_count, cache_miss_count, latency_tiera_ms, latency_tierb_ms.

## Tuning

- **alpha**: Higher → more vector, lower → more BM25. Use ~0.5 for balanced.
- **topN**: Larger → more recall, more Tier B work. Typical 100–200.
- **rerankN**: Final number of results. Typical 20–80.
- **weights**: Increase `tierB` if semantic precision matters most; increase `bm25` for keyword-heavy queries.

## Evidence Artifacts

### Example JSON response (score breakdown + trace)

```json
{
  "meta": { "request_id": "req_abc123", "as_of": "2025-02-02T12:00:00Z" },
  "data": {
    "results": [
      {
        "chunk_id": "chunk_1",
        "doc_id": "doc1",
        "snippet": "First chunk about markets...",
        "score_breakdown": { "tierA": 0.85, "bm25": 0.5, "tierB": 0.92, "cross": 0.0, "final": 0.78 },
        "metadata": {}
      }
    ],
    "trace": {
      "trace_id": "tr_abc123",
      "candidate_count": 200,
      "rerank_count": 80,
      "cache_hit_count": 45,
      "cache_miss_count": 35,
      "latency_tiera_ms": 120.5,
      "latency_tierb_ms": 890.2,
      "latency_cross_ms": 0.0,
      "filter_summary": {},
      "model_tiera": "openai:text-embedding-3-small",
      "model_tierb": "openai:text-embedding-3-large"
    }
  },
  "errors": []
}
```

### Sample log lines (trace_id + timings)

```
tiera_retrieval trace_id=tr_abc123 candidate_count=200 latency_ms=120.50 filter_summary={}
tierb_rerank trace_id=tr_abc123 rerank_count=80 cache_hits=45 cache_misses=35 latency_ms=890.20
advanced_search trace_id=tr_abc123 candidate_count=200 rerank_count=80 cache_hits=45 cache_misses=35 tiera_ms=120.50 tierb_ms=890.20
```
