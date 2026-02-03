# Log findings (errors and warnings)

Summary of recent Docker logs (`docker compose logs api worker`).

---

## Errors

### 1. `ValueError: could not convert string to float: '['` (worker)

- **Where:** `sentiment_api/ingest/cluster.py`, `find_nearest_cluster` (old line 37: `c = np.array(cvec, dtype=np.float32)`).
- **Cause:** pgvector returns cluster embeddings as strings (e.g. `"[0.1, 0.2, ...]"`). The old code did `np.array(cvec)` on that string, so NumPy iterated over characters and failed on `'['`.
- **Status in repo:** **Fixed.**  
  - `cluster.py` now uses `_to_float_vec(cvec)`, which parses strings with `json.loads()` and returns `None` for invalid values; invalid cluster vectors are skipped.  
  - `db/repo.py` `get_clusters_for_embedding()` also normalizes string embeddings to `list[float]` before returning.
- **Action:** Rebuild and redeploy the worker (and api if same image) so the running containers use the updated code:
  ```bash
  cd sentiment_api && docker compose build worker api && docker compose up -d worker api
  ```

---

## Warnings

### 2. LLM gpt-5-mini temperature unsupported

- **Message:** `LLM gpt-5-mini failed: ... 'temperature' does not support 0.1 with this model. Only the default (1) value is supported.`
- **Cause:** The client sent `temperature=0.1`; this model only accepts the default (1.0).
- **Status in repo:** **Fixed.** `sentiment_api/llm/client.py` catches this error and retries the same request with `temperature=1.0`.
- **Action:** Rebuild worker (and any service that calls the LLM) so the fix is in use.

### 3. Scrape 403 Forbidden (OECD)

- **Message:** `Scrape fetch failed https://www.oecd.org/newsroom/: Client error '403 Forbidden'`.
- **Cause:** The site is blocking the scraper (e.g. by User-Agent or IP).
- **Impact:** Articles from that source will not be ingested until the block is resolved or the source is disabled.
- **Action:** Optional — disable or replace the OECD source in the registry, or adjust scraping (e.g. User-Agent) if allowed by the site.

---

## Recommendation

1. Rebuild and restart workers (and api) to pick up the embedding and temperature fixes:
   ```bash
   cd sentiment_api && docker compose build worker api && docker compose up -d worker api
   ```
2. After that, the embedding and temperature errors/warnings in the logs should stop.
3. For OECD 403, either leave as-is (no ingest from that URL) or update the source config / scraping as needed.
