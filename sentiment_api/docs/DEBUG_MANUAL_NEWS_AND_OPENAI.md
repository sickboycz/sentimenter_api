# Debug manual: after-news pipeline, env vars, and OpenAI

Precise steps to debug the pipeline that runs **after** news is found (ingest → summarize → LLM/embeddings), see **environment variables** in the debugger, and verify how they reach the **OpenAI API**.

---

## 1. What runs where

| Step | Where it runs | What it does |
|------|----------------|---------------|
| News found (RSS/ingest) | Daemon or API (admin ingest) | Pushes job to Redis `QUEUE_INGEST` |
| **process_ingest** | **Worker** | Normalize, insert article, push to `QUEUE_SUMMARIZE` |
| **process_summarize** | **Worker** | L1/L2/L3 summaries (OpenAI), embed (OpenAI), cluster, event |
| **call_chat** (summaries) | **Worker** | `llm/client.py` — reads `os.environ.get("OPENAI_API_KEY")` |
| **embed_text** | **Worker** | `llm/embeddings.py` — reads `os.environ.get("OPENAI_API_KEY")` |

To debug “after finding news” you must attach to the **Worker** (port **5679**), not only the API (5678).

---

## 2. Precise steps to debug the Worker (after-news flow)

### 2.1 Start the stack in debug mode

From `sentiment_api/`:

```bash
docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d
```

Wait until API and worker are up (e.g. `docker compose -f docker-compose.yml -f docker-compose.debug.yml ps` shows healthy).

### 2.2 Attach Cursor to the Worker

1. **Run and Debug** (Ctrl+Shift+D / Cmd+Shift+D).
2. Choose **“Attach (Docker Worker)”** (port 5679).
3. Press **F5**. Status bar should show “Attached”.

### 2.3 Set breakpoints (after-news pipeline)

Set breakpoints in these files so execution stops **after** news is found and the worker picks the job:

| Order | File | Where | When it hits |
|-------|------|--------|----------------|
| 1 | `sentiment_api/ingest/worker.py` | First line inside `process_ingest` (e.g. `settings = get_settings()`) | Worker picked an ingest job (raw article just received). |
| 2 | `sentiment_api/ingest/worker.py` | First line inside `process_summarize` (e.g. `settings = get_settings()`) | Worker picked a summarize job (article will be summarized and embedded). |
| 3 | `sentiment_api/ingest/worker.py` | Line that calls `summarize_l1(...)` | Right before L1 summary (first LLM call). |
| 4 | `sentiment_api/llm/summaries.py` | First line inside `summarize_l1` or `summarize_l2` | Inside summary step. |
| 5 | `sentiment_api/llm/client.py` | First line inside `call_chat` (e.g. `key = os.environ.get(...)`) | Right before OpenAI Chat call; **best place to inspect env and key**. |
| 6 | `sentiment_api/llm/embeddings.py` | First line inside `embed_text` or inside `get_embedder` | Right before embedding (OpenAI or fallback). |

Suggested single breakpoint to see “after news” and env: **`sentiment_api/llm/client.py`**, first line of `call_chat` (where `key = os.environ.get("OPENAI_API_KEY")`).

### 2.4 Trigger a job so the Worker runs

Either:

- **Force ingest** from the Ops UI (if the frontend is running), or  
- **Admin API:**  
  `POST http://localhost:8080/v1/admin/ingest/run` (with API key if required).

That pushes ingest jobs; the worker will then push summarize jobs and process them. To hit **process_summarize** and **call_chat** quickly, you can also push a summarize job manually (e.g. from a script or by reusing an existing `article_id` + `norm` from DB). The normal flow is: ingest → summarize; so triggering ingest and waiting is enough.

---

## 3. Seeing environment variables in the debugger

### 3.1 Watch panel (always visible while stopped)

In Cursor, open **Run and Debug** → **WATCH** and add expressions. When execution stops at a breakpoint, these are evaluated:

| Expression | What you see |
|------------|----------------|
| `list(os.environ.keys())` | All env var names (no values, safe). |
| `os.environ.get("OPENAI_API_KEY", "")[:8] + "..." if os.environ.get("OPENAI_API_KEY") else "NOT SET"` | First 8 chars of key or "NOT SET" (safe to log). |
| `os.environ.get("SENTIMENT_API_OPENAI_API_KEY", "")[:8] + "..." if os.environ.get("SENTIMENT_API_OPENAI_API_KEY") else "NOT SET"` | Same for `SENTIMENT_API_*` alias. |
| `get_settings().model_dump()` | Full Pydantic settings (DB URL, Redis, **openai_api_key**, model IDs, etc.). **Note:** Masks secrets in dump depending on your Pydantic version; for raw value use the next line. |
| `get_settings().openai_api_key` | The key loaded by config (from `OPENAI_API_KEY` or `SENTIMENT_API_OPENAI_API_KEY`). |

To avoid typing, add one expression and duplicate it:

- **Env keys (safe):**  
  `{k: "SET" for k in ["OPENAI_API_KEY", "SENTIMENT_API_OPENAI_API_KEY", "DEBUG_ATTACH"] if os.environ.get(k)}`
- **Config vs env:**  
  `(get_settings().openai_api_key is not None, os.environ.get("OPENAI_API_KEY") is not None)`

### 3.2 Debug Console (when stopped)

Run the same expressions in the **DEBUG CONSOLE** (e.g. `get_settings().model_dump()` or the env checks above). You can also inspect `key` in `call_chat` (mask it: `key[:8] + "..." if key else "None"`).

---

## 4. How env vars reach the OpenAI API (investigation)

### 4.1 Current behavior

- **Config** (`sentiment_api/config.py`):  
  `openai_api_key` is loaded from **`OPENAI_API_KEY`** or **`SENTIMENT_API_OPENAI_API_KEY`** (Pydantic `AliasChoices`).
- **LLM Chat** (`sentiment_api/llm/client.py`):  
  Uses **only** `os.environ.get("OPENAI_API_KEY")` — **does not** use `get_settings().openai_api_key`.
- **Embeddings** (`sentiment_api/llm/embeddings.py`):  
  `get_embedder(..., api_key=...)`; when `api_key` is not passed (e.g. from worker), it uses **only** `os.environ.get("OPENAI_API_KEY")` — **does not** use config.

So: **OpenAI is driven by the process environment**, not by the config object. If you set only `SENTIMENT_API_OPENAI_API_KEY` in Docker Compose and not `OPENAI_API_KEY`, the API health check (which may use config) could see the key while the worker’s `call_chat` and `embed_text` would not, because they read `OPENAI_API_KEY`.

### 4.2 How to verify in the debugger

1. Attach to the **Worker** (Attach Docker Worker, port 5679).
2. Set a breakpoint in **`sentiment_api/llm/client.py`** on the line:  
   `key = os.environ.get("OPENAI_API_KEY")`.
3. Trigger the pipeline (ingest → summarize) so the worker runs summarize and hits `call_chat`.
4. When stopped:
   - Check **`key`** (value passed to `OpenAI(api_key=key)`). If it’s `None` or empty, the worker is not getting the key from env.
   - In **Watch**, compare:
     - `os.environ.get("OPENAI_API_KEY") is not None`
     - `get_settings().openai_api_key is not None`
   - If config has the key but `key` is empty, the code path is using env only and not config.

### 4.3 Ideas to fix / harden

1. **Use config in LLM code (recommended):**  
   In `llm/client.py` and `llm/embeddings.py`, use:
   - `key = get_settings().openai_api_key or os.environ.get("OPENAI_API_KEY")`  
   so both `OPENAI_API_KEY` and `SENTIMENT_API_OPENAI_API_KEY` (via config) are respected.
2. **Docker Compose:**  
   Ensure the **worker** service has the same env as the API, e.g.:
   - `OPENAI_API_KEY: ${OPENAI_API_KEY:-}`  
   (base `docker-compose.yml` already passes this to the worker; debug overlay keeps the same env.)
3. **Debug-only log:**  
   When `DEBUG_ATTACH=1` or `DEBUG_LOG=1`, log one line at startup in the worker: “OpenAI key: SET” or “OpenAI key: NOT SET” (no value), so you can confirm from logs without a debugger.
4. **Health check:**  
   The API’s `/v1/health` already validates the OpenAI key by calling the API. The worker has no HTTP health; the above log or a small “worker startup check” that tries one cheap OpenAI call (or only checks env) would make misconfiguration obvious.

---

## 5. Quick reference

| Goal | Action |
|------|--------|
| Debug **API** (HTTP handlers) | Attach **“Attach (Docker FastAPI)”** (port 5678). |
| Debug **Worker** (after-news: ingest → summarize → LLM/embed) | Attach **“Attach (Docker Worker)”** (port 5679). |
| See env vars anytime | Add Watch expressions (e.g. `get_settings().model_dump()`, env-key checks above). |
| See if key reaches OpenAI | Breakpoint in `llm/client.py` in `call_chat` and inspect `key` and env. |
| Trigger pipeline | Use Ops “Force Ingest” or `POST /v1/admin/ingest/run`. |

**pathMappings:** If your workspace is the parent repo (e.g. `Sentimenter`), set `localRoot` to `"${workspaceFolder}/sentiment_api"` and `remoteRoot` to `"/app"` for both attach configs.
