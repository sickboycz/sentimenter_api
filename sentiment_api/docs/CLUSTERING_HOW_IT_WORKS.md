# How clusters are made

Step-by-step flow and how to tune for “same story across outlets” vs “near-duplicate only”.

---

## Flow (summarize worker)

1. **Article** is summarized (L1, L2), then **embedded** (title + content, max 4000 chars).
2. **Existing clusters** are loaded: `get_clusters_for_embedding(conn, limit=200, model_id)` returns `(cluster_id, embedding, last_seen)` for each cluster (one embedding per cluster).
3. **Nearest cluster** is found by **cosine similarity**: `find_nearest_cluster(article_embedding, clusters_data, threshold=CLUSTER_SIMILARITY_THRESHOLD)`.
   - If some cluster has similarity **> threshold** → article is **merged** into that cluster (`cid = nearest`).
   - If no cluster has similarity > threshold → **new cluster** is created (`cid = cluster_id(canonical_story_key, first_seen)`).
4. Cluster row is upserted (`insert_cluster`), article is linked (`add_cluster_member`), and the **cluster’s embedding is set to this article’s embedding** (`insert_embedding(..., "cluster", cid, ...)`). So each cluster has a single vector; when you add a member, that vector is **overwritten** with the new article’s embedding (not a centroid).
5. Event and expectations are inserted; job is pushed to the index queue.

So: **one embedding per cluster**, and it is the **last article** that was merged into that cluster (or the first if it was never merged).

---

## Two-threshold idea

- **Topic cluster threshold (~0.86–0.92):** “Same story, different wording” across outlets. Default **0.88** — merge when similarity > 0.88 so you get many clusters (one per story), not one giant cluster.
- **Dedup threshold (0.95–0.98):** Near-identical reposts. If you set threshold to 0.95+, you effectively only merge near-duplicates; different outlets covering the same story often sit at 0.80–0.92, so you get **1 cluster** and everything else as “new” (or one cluster that slowly absorbs broad matches).

**Rule of thumb:** For a “world events” style engine, use **0.88** (topic clustering). For strict dedup-only, use 0.95+.

---

## Why you might see only 1 cluster

- **Threshold too high (e.g. 0.95):** Only near-duplicates merge. Different articles about the same event rarely reach 0.95, so almost nothing merges → one cluster (or many tiny clusters). **Fix:** lower to **0.88**.
- **Threshold too low (e.g. 0.82):** Everything merges into a few broad clusters. **Fix:** raise to 0.88–0.90.
- **Cluster vector = last merged article:** You compare to the last member’s embedding. If that article is broad, the next broad article can match and merge again.

---

## What to do

1. **Use topic clustering (default 0.88)**  
   Merge when similarity > 0.88 so “same story, different wording” forms one cluster. Set `CLUSTER_SIMILARITY_THRESHOLD=0.88` (default) or 0.86–0.92.
2. **Check worker logs**  
   Logs show `best_sim` when merging vs creating a new cluster. If most top matches are 0.80–0.92 and almost none ≥ 0.95, 0.88 is appropriate. If you see many ≥ 0.95 but still only 1 cluster, check DB/insert logic.
3. **Reset and re-run (optional)**  
   For a clean slate: reset DB (e.g. `scripts/reset_db_fresh.sh`), then re-ingest and re-summarize.

---

## Config

| Env | Default | Effect |
|-----|--------|--------|
| `CLUSTER_SIMILARITY_THRESHOLD` | `0.88` | Merge into cluster if cosine similarity **>** this. 0.88 = topic clustering; 0.95+ = dedup only. |

Relevant code: `sentiment_api/ingest/worker.py` (process_summarize), `sentiment_api/ingest/cluster.py` (find_nearest_cluster), `sentiment_api/db/repo.py` (get_clusters_for_embedding, insert_embedding).

---

## Summary dedupe and runs

- **Summaries:** Uniqueness is `(object_type, object_id, level, dedupe_key)`. `dedupe_key` is a hash of `(object_id, content_hash, schema_version, model)` so the same article + level + model does not create duplicate rows. `INSERT ... ON CONFLICT (object_type, object_id, level, dedupe_key) DO NOTHING` is used. Multiple rows per article are expected: L1 and L2 per article, plus L3 per cluster.
- **Runs:** Each ingest/summarize job records a run. High run count with few new articles is normal if the daemon polls often and often finds nothing new; empty runs are cheap (no embedding/summarization when nothing is queued).
