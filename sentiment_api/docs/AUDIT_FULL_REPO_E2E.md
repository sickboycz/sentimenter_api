# Full Repo Audit: Exceptions, Parsing, Categorization, API Health E2E

**Date:** 2026-02-03  
**Scope:** `sentiment_api/` — every file, endpoint, loop. Unhandled exceptions, wrong parsing, categorizing issues, API health E2E.

---

## Executive summary

| Severity | Count | Category |
|----------|-------|----------|
| Critical | 2 | Unhandled parse/load exceptions → 500 |
| High | 4 | Swallowed exceptions, IndexError risks |
| Medium | 6 | Edge cases, missing validation |
| Low | 8+ | Bare `pass`, over-broad catch |

---

## 1. CRITICAL: Unhandled exceptions

### 1.1 Registry loader: `_get_registry()` only catches `RegistryError`

**Location:** `sentiment_api/api/main.py` lines 143–149, `registry/loader.py` lines 89–93

**Issue:** `load_registry()` can raise:
- `json.JSONDecodeError` — malformed JSON registry
- `yaml.YAMLError` — malformed YAML
- `OSError` — permission / read error

`_get_registry()` catches **only** `RegistryError`. Any of the above will propagate as 500 on:
- `GET /v1/sources`
- `POST /v1/admin/ingest/run`
- `GET /v1/admin/ingest/run` (and other admin endpoints that load registry)

**Fix:** In `_get_registry()`, catch `Exception` and return `None` (or log and re-raise as `RegistryError`):

```python
def _get_registry():
    try:
        return load_registry(settings.source_registry_path)
    except (RegistryError, json.JSONDecodeError, yaml.YAMLError, OSError) as e:
        logging.getLogger("sentiment_api").warning("Registry load failed: %s", e)
        return None
```

---

### 1.2 Registry loader schema: `_load_json_schema()` — unguarded `json.loads`

**Location:** `sentiment_api/registry/loader.py` line 42

**Issue:** `json.loads(schema_path.read_text())` has no try/except. If `source_registry.schema.json` is malformed or missing, `JSONDecodeError` propagates when any registry load runs.

**Fix:** Wrap in try/except and return `{}` on failure (validation is optional).

---

## 2. HIGH: Swallowed exceptions & IndexError risks

### 2.1 Worker: `json.loads(data)` on malformed queue payload

**Location:** `sentiment_api/ingest/worker.py` line 305

**Issue:** `payload = json.loads(data) if isinstance(data, str) else data` — `json.loads` can raise `JSONDecodeError` on malformed JSON. The outer `except Exception` catches it and logs, but the job is **lost** (never retried). Malformed payloads in Redis will be dropped silently.

**Fix:** Catch `json.JSONDecodeError` explicitly, log with payload preview, and optionally re-queue to a dead-letter or discard with a metric.

---

### 2.2 RSS collector: `val[0].get("value", "")` — `val[0]` may not be a dict

**Location:** `sentiment_api/collectors/rss.py` lines 55–56

**Issue:**
```python
if isinstance(val, list) and val:
    content = val[0].get("value", "")
```

If `val[0]` is a string (e.g. some RSS entries), `.get` raises `AttributeError`. The loop has no try/except.

**Fix:**
```python
if isinstance(val, list) and val:
    first = val[0]
    content = first.get("value", first) if isinstance(first, dict) else str(first)
```

---

### 2.3 GDELT collector: `resp.json()` on non-JSON response

**Location:** `sentiment_api/collectors/gdelt.py` line 38

**Issue:** `data = resp.json()` — if the API returns 200 with HTML (e.g. error page), `JSONDecodeError` is raised. The `collect()` try/except catches it and logs, so the daemon continues. This is acceptable, but the error message "Expecting value: line 1 column 1 (char 0)" (seen in production) confirms this path is hit.

**Recommendation:** Consider `response.raise_for_status()` before `resp.json()` or explicit handling of non-JSON bodies to improve diagnostics.

---

### 2.4 LLM client: `resp.choices[0].message.content` — empty choices

**Location:** `sentiment_api/llm/client.py` line 39

**Issue:** If the API returns `choices=[]` or `choices` is missing, `IndexError` can occur.

**Fix:** Guard with `choices and len(choices) > 0` or use `.get()` with a default.

---

## 3. MEDIUM: Edge cases & missing validation

### 3.1 Worker `event_type`: `(topics + imp.get("reason_codes", []))[0]`

**Location:** `sentiment_api/ingest/worker.py` line 204

**Issue:** Logic is `(...)[0] if (topics or imp.get("reason_codes")) else "OTHER"`. If `topics = [""]` or reason_codes = `[""]`, `[0]` is valid. Safe as written; no change needed.

---

### 3.2 Outcomes / research: division by zero

**Locations:** `sentiment_api/engines/outcomes.py` line 50, `engines/research.py` line 72

**Issue:** `(bars[-1]["close"] - bars[0]["open"]) / float(bars[0]["open"]) if bars[0]["open"] else 0` — guarded, but if `bars` is empty, `bars[-1]` and `bars[0]` raise `IndexError`.

**Fix:** Add `if not bars: return 0` before the calculation.

---

### 3.3 Engine index: `values[0]` with empty rows

**Location:** `sentiment_api/engines/index.py` lines 67–74

**Issue:** `if not rows: return` guards empty rows. `values = [float(r["index_value"]) for r in rows]` — if all `index_value` are `None` or invalid, `float(None)` raises. Unlikely but possible.

---

### 3.4 API `/v1/impacts/latest`: `since` / `until` parsing

**Location:** `sentiment_api/api/main.py` lines 802–803

**Issue:** `dt.fromisoformat(since.replace("Z", "+00:00"))` — if `since` has invalid format, `ValueError` propagates. The endpoint catches `Exception` and returns an error envelope, so 500 is avoided but the error message may be unclear.

**Recommendation:** Validate date format before parsing or catch `ValueError` and return a 400 with a clear message.

---

### 3.5 Normalize: `item.fetched_at.tzinfo`

**Location:** `sentiment_api/ingest/normalize.py` line 117

**Issue:** `item.fetched_at.replace(tzinfo=timezone.utc) if item.fetched_at.tzinfo is None else item.fetched_at` — if `item.fetched_at` is `None`, `AttributeError`.

**Fix:** Add `if item.fetched_at is None: ...` or use `getattr(item.fetched_at, "tzinfo", None)`.

---

### 3.6 Asset targeting: `rows[0]["cluster_id"]` with empty rows

**Location:** `sentiment_api/engines/asset_targeting.py` line 237

**Issue:** `bundle = await get_asset_impacts_for_cluster(rows[0]["cluster_id"], ...)` — if `rows` is empty, `IndexError`.

**Fix:** Check `if not rows: return ...` before accessing `rows[0]`.

---

## 4. Swallowed exceptions (bare `pass` / broad `except`)

| File | Line | Context |
|------|------|---------|
| `api/main.py` | 169, 299, 693, 725, 1109, 1117, 1131, 1246, 1547, 1552, 1557, 1561, 1565, 1590 | `except Exception: pass` — errors hidden |
| `worker.py` | 54–55, 98–99, 320–321 | Heartbeat / run_id / finally |
| `daemon.py` | 24–25, 114–115, 126–127, 191–192 | Heartbeat, record_cycle |
| `keys.py` | 27–28, 42, 70–71 | API key validation |
| `yahoo_finance.py` | 45–46, 78–79, 104–105, 120–121 | External API failures |
| `registry/models.py` | 74 | Fallback in model |
| `llm/summaries.py` | 23 | JSON extract fallback |

**Recommendation:** Replace critical `pass` with at least `logger.debug(...)` or `logger.warning(...)` so failures are observable.

---

## 5. API health E2E

### 5.1 Health endpoint (`GET /v1/health`)

- DB, Redis, registry, artifacts, OpenAI each wrapped in try/except.
- Returns `status: ok | degraded | down` based on core checks.
- Postgres failure → `status: down`.
- **Gap:** No timeout on Redis `ping()` or DB `SELECT 1` — slow dependencies can stall the handler.

---

### 5.2 Status endpoint (`GET /v1/status`)

- Calls `health()` then overlays ingestion/allocation from `runs`.
- Ingestion = last ingest run in 15 min; allocation = last summarize run in 30 min.
- **Gap:** If worker never processes summarize (e.g. queue priority bug), allocation stays "unknown" even when articles exist. This matches the observed behavior and was addressed with the queue-order fix.

---

### 5.3 Ready probe (`GET /ready`)

- Returns 503 if pool is None or DB check fails.
- Sufficient for Kubernetes readiness.

---

### 5.4 Contract tests

- `test_contract_responses.py` validates health, status, mood/now, impacts/latest, universes against JSON schemas.
- **Gap:** No E2E test that starts the full stack (API + worker + daemon + Redis + Postgres) and asserts end-to-end flow (ingest → summarize → clusters). Integration tests exist for advanced search but not for the main pipeline.

---

## 6. Categorization / routing

### 6.1 Impact scoring: topic → direction

**Location:** `sentiment_api/llm/impact.py` `_direction_from_topics()`

- `risk_off` / `risk_on` tag sets are hardcoded.
- `str(channels)` and `str(topics)` used for substring checks — brittle if formats change.

### 6.2 Source credibility / license mapping

**Location:** `sentiment_api/api/main.py` lines 1305–1306

- `cred_map` and `lic_map` — unknown values fall back to `"reputable_media"` and `"open"`.
- Ensures a valid value; no bug, but worth documenting.

### 6.3 Event type from topics

**Location:** `sentiment_api/ingest/worker.py` line 222

- `event_type = (topics + imp.get("reason_codes", []))[0] if ... else "OTHER"` — safe with the `else "OTHER"` branch.

---

## 7. Recommended fixes (priority order)

1. **P0 —** Extend `_get_registry()` to catch `JSONDecodeError`, `YAMLError`, `OSError` and return `None` (or log and treat as registry unavailable).
2. **P0 —** Guard `_load_json_schema()` with try/except; return `{}` on failure.
3. **P1 —** In RSS collector, guard `val[0].get(...)` for non-dict `val[0]`.
4. **P1 —** In LLM client, guard `resp.choices[0]` against empty/missing `choices`.
5. **P2 —** Add `if not bars:` in outcomes/research before indexing `bars[0]` / `bars[-1]`.
6. **P2 —** Add `if not rows:` in asset_targeting before `rows[0]["cluster_id"]`.
7. **P2 —** Normalize: handle `item.fetched_at is None` before accessing `.tzinfo`.
8. **P3 —** Replace critical bare `pass` with logging.
9. **P3 —** Add E2E test for ingest → summarize → clusters flow.

---

## 8. Files audited

| Path | Notes |
|------|-------|
| `api/main.py` | 60+ endpoints, health, status, exception handlers |
| `api/auth.py`, `keys.py`, `rate_limit.py`, `idempotency.py` | Auth and middleware |
| `ingest/worker.py`, `daemon.py`, `backfill.py`, `normalize.py` | Pipeline |
| `collectors/gdelt.py`, `rss.py`, `scrape.py`, `http_client.py` | Data collection |
| `registry/loader.py`, `models.py` | Registry loading |
| `llm/summaries.py`, `impact.py`, `client.py`, `embeddings.py` | LLM and scoring |
| `db/pool.py`, `repo.py` | Database |
| `engines/asset_targeting.py`, `index.py`, `outcomes.py`, `research.py` | Business logic |
| `queue/client.py` | Redis queues |

---

*End of audit.*
