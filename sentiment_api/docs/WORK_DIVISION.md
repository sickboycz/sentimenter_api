# Work division by queue depth (E2E flow)

Workers divide work based on **weighted queue depth**: they prefer queues with the highest **depth × stage_weight**, so more workers go to earlier stages and fewer to later ones. That matches the E2E funnel: news volume **reduces at each gate** (dedupe, cluster, etc.), so we want more capacity at ingest and less at index.

## E2E flow and why stage weights

- **Pipeline:** Daemon → **ingest** (raw items) → **normalize** (optional) → **summarize** (articles → clusters) → **score** → **index** (timeseries).
- **Volume:** Ingest has the most work (many feeds, many items). After normalize/dedupe and clustering, fewer items reach summarize and far fewer reach score/index. So we assign **more workers to earlier stages** and fewer to later.
- **Default weights:** `ingest:4`, `normalize:3`, `summarize:2`, `score:1`, `index:1`. Poll order is by **(depth × weight) descending** among queues under their cap.
- **Stage caps:** Max workers per queue so you get flow (examples: 6 workers → 3,2,1; 7→4,2,1; 8→4,2,2; 9→4,3,2; 10→5,3,2). **When there's no work at a level (depth 0), workers take work from other queues; when work appears they go back** so the whole pipeline keeps flowing. Default presets by worker count: see table below.
- **Default weights (values):** `ingest:4`, `normalize:3`, `summarize:2`, `score:1`, `index:1`. Poll order is by **(depth × weight) descending**. So when ingest has 100 and summarize has 50, effective priority is 400 vs 100 → workers prefer ingest. As ingest drains, summarize (and then score/index) get workers. Result: a nice E2E flow instead of “all workers on ingest” or “all on one queue”.

## How it works

- **Queues:** `ingest` → `normalize` → `summarize` → `score` → `index` (Redis lists).
- **When QUEUE_WORK_DIVISION is true:** Before each `blpop`, the worker fetches queue lengths and **current workers per queue** (from Redis worker keys, last_job + last_seen within 90s). It only considers queues where workers_on_queue < cap; then orders by **(depth × stage_weight) descending** and polls. **Empty queues stay in the list** (priority 0), so workers take work from other levels when one has no work; when work appears, priority rises and workers go back.
- **When false:** Fixed order (summarize, index, score, ingest, normalize) — downstream-first, no weighting.

## Configuration

| Env | Default | Description |
|-----|---------|-------------|
| **QUEUE_WORK_DIVISION** | `true` | When `true`, workers poll by weighted depth with stage caps. When `false`, fixed order. |
| **QUEUE_STAGE_WEIGHTS** | `ingest:4,normalize:3,summarize:2,score:1,index:1` | Comma-separated `stage:weight`. Higher weight = more workers at that stage. |
| **QUEUE_STAGE_CAPS** | `ingest:3,summarize:2,index:1` | Fixed caps when QUEUE_STAGE_CAPS_BY_WORKERS is unset or disabled. |
| **QUEUE_STAGE_CAPS_BY_WORKERS** | 6→3,2,1 … 10→5,3,2 | Space-separated `N:ingest:x,summarize:y,index:z`. Caps by total worker count (default presets for 6–10). Set `""` to use only QUEUE_STAGE_CAPS. |

**Example caps by worker count (default presets):**

| Workers | Ingest | Summarize | Index |
|--------|--------|-----------|-------|
| 6      | 3      | 2         | 1     |
| 7      | 4      | 2         | 1     |
| 8      | 4      | 2         | 2     |
| 9      | 4      | 3         | 2     |
| 10     | 5      | 3         | 2     |

To use the fixed order (no weighting):

```bash
SENTIMENT_API_QUEUE_WORK_DIVISION=false
```

To give ingest even more relative capacity (e.g. 6 workers on ingest, 1 on index):

```bash
SENTIMENT_API_QUEUE_STAGE_WEIGHTS=ingest:6,normalize:4,summarize:2,score:1,index:1
```

## Ops

- **GET /v1/admin/ops** returns `queues` (depth per queue), `queues_total`, **`workers`** (list of worker instances with `id`, `last_seen`, `age_sec`, `last_job`, `counts`), **`system`** (CPU, memory, disk % and GB), and **`desired_workers`** (set by scale API). Use the ops page **Workers** card to see the list and **System monitoring** for CPU/memory/disk.
- **Worker scale from UI:** The ops page +/- buttons call **POST /v1/admin/scale/workers** with `{"count": N}`. The API stores desired count in Redis and, when **COMPOSE_PROJECT_DIR** is set and the API has Docker access, runs `docker compose up -d --scale worker=N` so scaling applies immediately. **To enable scale-from-API:** (1) API image includes the Docker CLI (default). (2) In `docker-compose.yml`, the API service mounts `/var/run/docker.sock` and the project dir as `/workspace`, and sets `COMPOSE_PROJECT_DIR=/workspace`. Then the +/- buttons actually scale workers. Otherwise run manually: `docker compose up -d --scale worker=N`.
- **Worker id:** Each worker registers with a unique id (`WORKER_ID` env or `hostname-pid`). Scaled Docker Compose workers get distinct hostnames (e.g. `sentiment_api-worker-1`, `sentiment_api-worker-2`).
- **Prometheus:** `queue_depth{name="..."}` gauges are updated by the API when it serves `/metrics` (and by the daemon for ingest). Workers do not export metrics; they only consume using the dynamic order.

## Cost / performance

- One pipeline of `LLEN` per poll (5 keys). Overhead is small. No caching is used; order is recomputed every loop so it reacts quickly to queue growth.
