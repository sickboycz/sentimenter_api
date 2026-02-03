# Debugging the FastAPI Backend in Docker (debugpy + Cursor)

This document describes how to run the API in debug mode and attach from Cursor (VS Code–style) for breakpoints and watch variables.

## Requirements

- Docker and Docker Compose (run from `sentiment_api/`).
- Cursor (or VS Code) with the Python / debugpy extension.

## Normal mode (no debugger)

From `sentiment_api/`:

```bash
docker compose up -d
```

API listens on port 8080; no debug port is opened.

## Debug mode (attach from Cursor)

1. **Rebuild API and Worker with debugpy, then start** (from `sentiment_api/`):

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.debug.yml build --no-cache api worker
   docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d
   ```

   Or start without forcing a full rebuild (uses cache if images exist):

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d
   ```

   This builds the API image with `debugpy` installed, sets `DEBUG_ATTACH=1`, exposes port **5678**, and mounts the repo at `/app` so breakpoints bind to your local files.

2. **Wait for the API to be ready** (e.g. health check passes). Optional: run the verification script (see below).

3. **Attach in Cursor**:
   - Open the **Run and Debug** view (Ctrl+Shift+D / Cmd+Shift+D).
   - Select the **"Attach (Docker FastAPI)"** configuration.
   - Press **F5** (or click the green play button).
   - You should see “Attached” in the status bar.

4. **Set a breakpoint** (e.g. in `sentiment_api/api/main.py` on the first line of the `@app.get("/v1/health")` handler) and send a request:

   ```bash
   curl -s http://localhost:8080/v1/health
   ```

   Execution should stop at the breakpoint.

## Optional: block until a debugger attaches

By default the API does **not** wait for a client; it starts immediately. To make the process block until Cursor attaches, set:

```bash
DEBUG_WAIT=1
```

(e.g. in `docker-compose.debug.yml` under `api.environment` or in a `.env` file used by Compose). Then start the debug config in Cursor before or shortly after the container starts.

## Verification script

From `sentiment_api/` with the **debug** stack running:

```bash
python scripts/verify_debug_attach.py
```

This checks that:
- Port 5678 is listening inside the API container.
- `GET http://localhost:8080/v1/health` returns 200.

On success it prints `PASS` lines and reminds you to attach to `127.0.0.1:5678`.

**Quick checklist:**
1. `docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d`
2. `python scripts/verify_debug_attach.py` (optional)
3. In Cursor: Run and Debug → “Attach (Docker FastAPI)” → F5
4. Set a breakpoint (e.g. in `sentiment_api/api/main.py` in the `/v1/health` handler) and hit the API.

## Why breakpoints might not hit

| Cause | What to do |
|-------|------------|
| **Uvicorn `--reload` or multiple workers** | Debug mode uses a single process and no reload. The debug overlay does not add `--reload` or `--workers`. If you changed the command, remove them for the API service in debug. |
| **No volume mount** | Breakpoints are resolved using path mappings. The debug overlay mounts `.:/app`. If you run without it, the container has a copy of the code and paths may not match; use the debug overlay so `/app` is your repo. |
| **Wrong `remoteRoot`** | The launch config maps `${workspaceFolder}` → `/app`. If your Cursor workspace is the **parent** repo (e.g. `Sentimenter`), set `pathMappings` to `localRoot: "${workspaceFolder}/sentiment_api"` and `remoteRoot: "/app"` so files under `sentiment_api/` match the container. |
| **Debugger not attached** | Start the “Attach (Docker FastAPI)” config before or while triggering the code path. |
| **Different code path** | Ensure the request actually hits the handler where the breakpoint is (e.g. use `/v1/health` or the route you added the breakpoint to). |

## Security

**Do not expose port 5678 to the public internet.** The debug port allows arbitrary code execution in the API process. Use it only on localhost or a trusted network (e.g. bind to `127.0.0.1` inside the container if needed; the default `debugpy.listen(("0.0.0.0", 5678))` listens on all interfaces inside the container, but Docker maps it to the host; keep the host firewall or Compose port binding so that 5678 is not reachable from outside).

## Debugging the Worker (after-news pipeline)

The **Worker** runs ingest → summarize → LLM/embeddings. To debug that flow (breakpoints in `process_ingest`, `process_summarize`, `call_chat`, `embed_text`) and to inspect env vars / OpenAI key:

- Use the same debug overlay; the Worker listens on port **5679**.
- In Cursor, select **“Attach (Docker Worker)”** and press F5.
- See **docs/DEBUG_MANUAL_NEWS_AND_OPENAI.md** for a precise step-by-step, breakpoint map, how to see environment variables, and how env vars reach the OpenAI API.

## Summary

- **Normal:** `docker compose up -d`
- **Debug:** `docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d` then attach in Cursor:
  - **API:** “Attach (Docker FastAPI)” → `127.0.0.1:5678`
  - **Worker (after-news):** “Attach (Docker Worker)” → `127.0.0.1:5679`
- **pathMappings:** `localRoot` = workspace (or `workspace/sentiment_api` if workspace is parent repo), `remoteRoot` = `/app`.
