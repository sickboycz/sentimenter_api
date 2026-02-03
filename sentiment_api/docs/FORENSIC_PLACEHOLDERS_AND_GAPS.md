# Forensic Report: Placeholders and Missing Implementation

**Scope:** sentiment_api repo (backend + frontend + docs).  
**Focus:** Stubs, placeholders, silent `pass`, empty returns, and documented gaps.

**Update:** We use **Weaviate** (and pgvector); Pinecone is not used. Cluster narrative fields are populated from L3 summaries; silent failures in API now log at DEBUG/WARNING. Frontend search remains UI-only by design.

---

## 1. Stubs / Incomplete Backends

| Location | Finding | Severity |
|----------|---------|----------|
| **`sentiment_api/vector_store/pinecone_client.py`** | Optional backend; **not used in production**. Clustering uses Weaviate or pgvector only. `get_cluster_vectors()` returns `[]`; docstring states clustering is not supported with Pinecone. | **None** — Weaviate/pgvector only. |
| **`sentiment_api/retrieval/cross_encoder.py`** | Only `NoOpCrossEncoder` (always `score() == 0.0`). Docstring: "No-op by default." No real reranker model wired. | **Low** — Intentional placeholder; pipeline uses it and doc says "plug real model when available." |

---

## 2. Silent Exception Handling (`except: pass` or equivalent)

| Location | Context | Risk |
|----------|---------|------|
| **`api/main.py`** ~819 | `get_asset_impacts_for_cluster(cluster_id)` — on any exception, `asset_impacts` stays `None`; response still returns. | **Low** — Caller can see `asset_impacts: null`; no crash. |
| **`api/main.py`** ~1202–1213 | SSE stream: fetch sentiment_timeseries / latest_asset_impacts — on exception, payload stays previous or `{}`. | **Low** — Stream continues; client may see stale/empty payload. |
| **`api/main.py`** ~1392 | `search/advanced` body: `weights` JSON parse failure → `pass`, then `weights` remains `None` (config default used). | **Low** — Intentional fallback. |
| **`api/main.py`** ~1815–1858 | `/v1/admin/ops` DB stats: each metric (articles, clusters, events, summaries, runs) in try/except; on failure that metric skipped, rest still returned. | **Low** — Partial stats; ops page may show missing counts. |
| **`api/keys.py`** ~28 | `_verify_key`: Argon2 verify fails → `pass`, then fallback to SHA256 comparison. | **Low** — Documented fallback when argon2 unavailable. |
| **`api/keys.py`** ~73 | `validate_api_key`: DB update `last_used_at` fails → `pass`; key still accepted. | **Low** — Auth succeeds; only last_used not updated. |
| **`retrieval/tiera_retrieval.py`** ~122 | Parsing Weaviate `explain_score` (e.g. bm25) — on exception, `bm25_score` stays 0. | **Low** — Hybrid score still has vector component. |
| **`registry/models.py`** ~75 | `Source.model_post_init`: empty `pass` (comment: "Type-specific URL requirements validated in load_registry"). | **None** — Pydantic hook; validation elsewhere. |
| **`registry/loader.py`** ~29 | `class RegistryError(Exception): pass` | **None** — Normal exception subclass. |
| **`collectors/rss.py`** ~53 | Parsing `published` from entry dates — on TypeError/ValueError, `pass`; `published_at` may stay None. | **Low** — Item still yielded with null date. |
| **`llm/summaries.py`** ~23 | `_extract_json`: JSON parse failure → `pass`; returns None. Caller handles None. | **Low** — Intentional. |
| **`logging_file.py`** ~33 | Adding file handler: on OSError (e.g. permission), `pass`; only stdout used. | **Low** — Optional file logging. |
| **`services/yahoo_finance.py`** ~46, 79, 105, 121 | Four blocks: summary, price, statistics, earnings. Each in try/except; on failure that section stays empty. | **Low** — Partial company detail returned. |

---

## 3. Hardcoded / Missing Response Fields (API)

| Endpoint | Field(s) | Value | Note |
|----------|----------|--------|------|
| **GET cluster by id** (`/v1/news/clusters/{id}`) | `what_changed_en`, `why_it_matters_en`, `what_to_watch_en`, `impact_explanation_en`, `summary_bullets_en` | From L3 summary | **Implemented:** `get_cluster_l3_summary()` fetches latest L3 summary; narrative fields and summary_bullets populated. |
| **GET cluster by id** | `historical_analogs` | `[]` or `None` (if not include_analogs) | Not implemented; optional. |

---

## 4. Frontend Placeholders / Stubs

| Location | Finding |
|----------|---------|
| **`frontend/components/Topbar.tsx`** | Search input: `placeholder="Search clusters, tickers…"`; state `q` is local only — **kept as-is** (no command palette, no API). |
| **Dashboard docs** | "Virtualization for large lists" — TODO in news/tickers; guardrails (limit 50). |

---

## 5. Intentional Empty / Protocol / Fallbacks (Not Gaps)

| Location | Purpose |
|----------|---------|
| **`retrieval/provider.py`** | `EmbeddingProvider` protocol uses `...`; `FakeEmbeddingProvider` for tests — by design. |
| **`retrieval/cross_encoder.py`** | `CrossEncoder` protocol `...`; `NoOpCrossEncoder` — documented placeholder. |
| **`vector_store/base.py`** | Protocol methods `...` — interface only. |
| **`llm/embeddings.py`** | "using deterministic mock" when sentence-transformers fails — fallback for dev. |
| **Various `return []` / `return {}` / `return None`** | After validation (e.g. empty input, cache miss, no rows) — correct behavior. |

---

## 6. Documented Gaps (from existing docs)

| Doc | Gaps mentioned |
|-----|-----------------|
| **DASHBOARD_IMPLEMENTATION_STATUS.md** | Global search stub; command palette not implemented; virtualization TODO for news/tickers. |
| **DASHBOARD_V2_INTEGRATION_REPORT.md** | Research/event study "placeholder" — but `engines/research.py` implements full event study (windows, returns, hit_rate). API and engine are implemented; dashboard may not surface it fully. |
| **MISSING_FILES_V1_2_ANALYSIS.md** | Lists v1.2 package files not in main repo and why (intentional omissions). |
| **PINECONE_WEAVIATE_INTEGRATION.md** | Reference for implementing Pinecone/Weaviate; Pinecone cluster-vector fetch still stub. |

---

## 7. Recommendations

1. **Vector store:** We use **Weaviate** (and pgvector). Pinecone is optional and not used for clustering; clustering requires Weaviate or pgvector.

2. **Cluster detail narrative:** **Done.** L3 summary is fetched via `get_cluster_l3_summary()`; `what_changed_en`, `why_it_matters_en`, `what_to_watch_en`, `impact_explanation_en`, and `summary_bullets_en` are populated in GET cluster by id.

3. **Historical analogs:** **Implemented** — `get_similar_clusters()` by embedding cosine similarity; returns up to 20 analogs with cluster_id, similarity, label_en, date.

4. **Frontend search:** Kept as UI-only (no command palette, no API) by design.

5. **Silent failures in API:** **Done.** Asset impacts, SSE mood/impacts, cluster articles fallback, and ops DB stats now log at DEBUG or WARNING.

6. **Cross-encoder:** **Implemented** — set `CROSS_ENCODER_MODEL` (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2`) to enable; pipeline uses it when `retrieval_weights` has `cross` > 0.

---

## 8. Summary Table

| Category | Count | Status |
|----------|-------|--------|
| Pinecone | 1 | Not used; Weaviate/pgvector only. Documented. |
| Cross-encoder no-op | 1 | Optional: set CROSS_ENCODER_MODEL to enable sentence-transformers reranker. |
| Silent exception handling | 13 | API paths now log (DEBUG/WARNING). |
| Cluster narrative in GET cluster by id | 1 | **Implemented** via L3 summary. |
| historical_analogs | 1 | **Implemented** — embedding-based similar clusters when include_analogs=true. |
| Frontend search | 1 | Kept as UI-only by design. |
| Documented TODOs (virtualization, etc.) | 2 | Track in dashboard/backlog. |

Weaviate is the vector store for clustering and retrieval. No critical missing paths for core ingestion → clustering → API flow.

---

## 9. Docs vs Implementation (2026-02-02)

See **FORENSIC_DOCS_VS_IMPLEMENTATION.md** for full comparison of `Docs/` packages to current state.  
Key completions: LLM Chunks debug endpoint now returns `prompt_hashes` and `schema_hashes`; LLM Chunks docs (10–130) copied to sentiment_api/docs as `LLM_CHUNKS_*.md`.
