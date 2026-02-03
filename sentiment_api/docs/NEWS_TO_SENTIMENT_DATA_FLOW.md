# News → Sentiment: Complete Data Flow

Step-by-step trace of how news flows from collection to sentiment, with data types, DB operations, and potential issues.

---

## Overview

```
[Sources] → Daemon (poll) → Redis QUEUE_INGEST → Worker process_ingest
    → Normalize → DB articles → Redis QUEUE_SUMMARIZE → Worker process_summarize
    → L1/L2 summaries → Embed → Cluster → DB clusters/events/embeddings
    → Redis QUEUE_INDEX → Worker process_index → sentiment_timeseries / sentiment_daily
```

---

## Step 1: Collection (Daemon + Collectors)

**Where:** `daemon.py` → `RSSCollector`, `GDELTCollector`, `ScrapeCollector`

**Input:** Registry sources (enabled, with feed_url / base_url / page_url)

**Output:** `RawItem` (dataclass)

| Field | Type | Source |
|-------|------|--------|
| source_id | str | source.source_id |
| source_type | str | "rss" \| "gdelt" \| "scrape" |
| url | str | entry link / art["url"] / item.url |
| published_at | datetime \| None | parsed from feed / art["seendate"] / scrape |
| fetched_at | datetime | now() |
| title_raw | str | entry.title / art["title"] / extracted |
| content_raw | str | content/summary/description |
| content_html | str | raw HTML (scrape) or "" |
| metadata | dict | e.g. {"feed_url": ...} |

**Parsing checks:**
- RSS: `published_parsed` / `updated_parsed` → `datetime(*ts[:6], tzinfo=timezone.utc)` — `ts` may have fewer than 6 elements; `ValueError`/`TypeError` caught.
- RSS content: `val[0].get("value", "")` — **fixed:** now handles non-dict `val[0]`.
- GDELT: `art.get("seendate")` → `datetime.strptime(ts[:10], "%Y%m%d")` — invalid format caught.
- GDELT `resp.json()` — on HTML/empty body → `JSONDecodeError`; caught in collect() try/except.

**Serialization for queue:**
```python
_serialize_item(item) → dict
  published_at → isoformat() | None
  fetched_at → isoformat()
```
Pushed as `json.dumps(_serialize_item(item))` to `QUEUE_INGEST`.

---

## Step 2: Ingest (Worker process_ingest)

**Input:** Redis payload (JSON string) → `payload: dict`

**Expected keys:** `source_id`, `url`, `title_raw`, `content_raw`, `content_html`, `published_at` (str), `fetched_at` (str), `source_type`, `metadata`

**Flow:**
1. `insert_run(conn, "ingest", payload["source_id"], {...})`
2. `load_registry(...)` — can raise; not caught here (worker will log and continue on next job)
3. **normalize_item(payload, reg.defaults, ...)**

### 2.1 Normalize

**Input:** `payload` (dict from queue) — same shape as `_serialize_item` output

**Parsing:**
- `_dt(v)` for `published_at` / `fetched_at`: `datetime.fromisoformat(v.replace("Z", "+00:00"))` — invalid ISO → `None`
- `fetched_at` defaults to `datetime.now(timezone.utc)` if None

**Output:** `norm: dict`

| Key | Type | Notes |
|-----|------|-------|
| source_id | str | |
| url, canonical_url | str | canonical_url from urljoin/urlparse |
| published_at | datetime \| None | |
| fetched_at | datetime | tz-aware |
| lang_original | str | langdetect or "en" |
| title_raw | str | |
| title_en | str | translated if non-en |
| content_en | str | |
| translation_status | str | "ok" \| "failed" |
| content_hash | str | SHA256 of title_en+content_en |

**Checks:** `norm["title_en"]` required (falls back to content_en[:200] or url). `norm["content_en"]` can be empty.

4. **article_id** = `article_id(source_id, canonical_url, pub_str)` — `art_<base32(hash)>`
5. **insert_article(conn, norm)** — expects `norm` with `article_id`, `source_id`, `url`, `canonical_url`, `fetched_at`, `title_en`, etc.

### 2.2 DB: insert_article

**Schema:** `articles(article_id, source_id, url, canonical_url, published_at, fetched_at, lang_original, title_raw, title_en, content_en, translation_status, translation_provider, translation_confidence, content_hash, metadata)`

**Return:** `art["article_id"]` on success. Docstring says "None if duplicate" but **ON CONFLICT DO NOTHING** does *not* raise `UniqueViolationError` — it always returns the id. So **duplicates are treated as inserts** and pushed to summarize.

**⚠️ Issue:** Duplicate articles (same URL+date) are still queued to summarize, causing redundant LLM calls and possible duplicate clusters (cluster_id includes first_seen).

6. If `inserted`: `save_l0(...)`, `insert_article_body(...)`
7. `finish_run(conn, run_id, "ok", {...})`
8. If `inserted`: **push to QUEUE_SUMMARIZE**

**Payload to summarize:**
```python
{"article_id": art_id, "source_id": norm["source_id"], "norm": norm}
```
Uses `_DateTimeEncoder` — datetimes become ISO strings in JSON.

---

## Step 3: Summarize (Worker process_summarize)

**Input:** `payload` from QUEUE_SUMMARIZE with `article_id`, `norm`

**norm after JSON round-trip:** `published_at`, `fetched_at` are **strings** (ISO), not datetime.

**Flow:**
1. `art_id = payload["article_id"]`, `norm = payload["norm"]`
2. `title = norm.get("title_en","")`, `content = norm.get("content_en","")`, `url = norm.get("url","")`
3. `pub_str = pub.isoformat() if hasattr(pub,"isoformat") else str(pub)` — handles string `pub`
4. **insert_run(conn, "summarize", art_id, {...})**
5. **summarize_l1(...)** → L1 dict
6. **summarize_l2(...)** → L2 dict
7. **insert_summary** (L1, L2)
8. **embed_text(title + content)** → list[float] (3072 dims)
9. **insert_embedding** (article, art_id, model, embedding)
10. **get_clusters_for_embedding(conn, 500, model_id)** → `list[(cluster_id, embedding, last_seen)]`
11. **find_nearest_cluster(embedding, clusters_data, 0.82)** → cluster_id or None
12. **canonical_story_key(headline, topics)** → ckey
13. If no nearest: **cluster_id(ckey, first_seen)** → new cid
14. **summarize_l3(...)** → L3 dict
15. **insert_summary** (cluster, cid, L3)
16. **score_impact(cid, l3, ...)** → impact dict
17. **insert_cluster**, **add_cluster_member**, **insert_embedding** (cluster)
18. **insert_event**, **insert_expectation**
19. Optional: asset targeting, **insert_event_impacts**
20. **finish_run**
21. **push to QUEUE_INDEX** `{"cluster_id": cid}`

### 3.1 L1/L2 Summaries (LLM)

**Input:** article_id, title_en, content_en, source_url, published_at (str)

**L1 output:** `{article_id, facts, uncertainty_flags}`
**L2 output:** `{article_id, headline_en, topics, regions, tone, key_claims_en, why_it_matters_en, entities, uncertainty_flags, evidence_refs}`

**LLM parsing:** `_extract_json(text)` — finds first `{` to last `}`, `json.loads`; on failure returns fallback dict.

### 3.2 Embedding

**Input:** `text = (title + content)[:4000]`
**Output:** 3072-dim list[float] (OpenAI or sentence-transformers or random fallback)

**⚠️** `embed_text` uses `resp.data[0].embedding` — if `data` is empty, `IndexError`.

### 3.3 Clustering

**get_clusters_for_embedding:** Returns `(cluster_id, embedding, last_seen)` for existing clusters. On cold start (0 clusters), returns `[]` → `find_nearest_cluster` returns None → new cluster.

**cluster_id:** `clu_<base32(hash(canonical_story_key|first_seen))>` — same story at different times → different cluster_id.

### 3.4 Impact scoring

**score_impact(l3, ...):** Topics/channels → direction (RiskOn/RiskOff/Neutral), severity, impact_score, impact_level, reason_codes, risk_vector.

**DB:** clusters, cluster_members, embeddings, events, expectations, event_impacts (optional).

---

## Step 4: Index (Worker process_index)

**Input:** `{"cluster_id": cid}`

**Flow:**
1. **compute_intraday_from_clusters("5m")** — aggregates clusters into sentiment_timeseries
2. **compute_daily_ohlc(date.today())** — sentiment_daily
3. **measure_outcomes("SPY")** — outcomes table

**DB tables:** `sentiment_timeseries`, `sentiment_daily`, `outcomes`

---

## Data Type Summary

| Stage | Key data | Types |
|-------|----------|-------|
| RawItem | url, title_raw, content_raw, published_at, fetched_at | str, datetime |
| Queue ingest | JSON | all primitives; dates as ISO strings |
| norm (after normalize) | title_en, content_en, published_at, fetched_at | str, datetime |
| Queue summarize | norm | JSON; dates as ISO strings |
| process_summarize norm | published_at, fetched_at | **str** (from JSON) |
| L1, L2, L3 | dict | from LLM or fallback |
| embedding | list[float] | 3072 dims |

---

## Parsing & Validation Checkpoints

| Location | What | Failure mode |
|----------|------|--------------|
| Daemon _serialize_item | datetime.isoformat | None → skipped |
| Worker json.loads(payload) | Queue data | JSONDecodeError → caught, job lost |
| normalize _dt() | ISO date strings | ValueError → None |
| summarize_l1/l2 _extract_json | LLM output | JSONDecodeError → fallback dict |
| insert_article | art keys | KeyError if missing required |
| insert_cluster/embedding | JSON for tone/impact | json.dumps handles dict |
| embed_text | OpenAI resp.data[0] | IndexError if empty |

---

## Recommended Fixes

1. **insert_article duplicate detection:** Use `INSERT ... ON CONFLICT DO NOTHING RETURNING article_id` and return None when no row returned, so duplicates are not pushed to summarize.
2. **embed_text:** Guard `resp.data[0]` against empty list.
3. **Worker payload:** Wrap `json.loads(data)` in try/except for `JSONDecodeError`; log and optionally dead-letter malformed jobs.

---

*End of flow.*
