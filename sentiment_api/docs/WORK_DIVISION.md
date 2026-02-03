# Work division by queue depth (E2E flow)

Workers divide work based on **weighted queue depth**: they prefer queues with the highest **depth × stage_weight**, so more workers go to earlier stages and fewer to later ones. That matches the E2E funnel: news volume **reduces at each gate** (dedupe, cluster, etc.), so we want more capacity at ingest and less at index.

## E2E flow and why stage weights

- **Pipeline:** Daemon → **ingest** (raw items) → **normalize** (optional) → **summarize** (articles → clusters) → **score** → **index** (timeseries).
- **Volume:** Ingest has the most work (many feeds, many items). After normalize/dedupe and clustering, fewer items reach summarize and far fewer reach score/index. So we assign **more workers to earlier stages** and fewer to later.
- **Default weights:** `ingest:4`, `normalize:3`, `summarize:2`, `score:1`, `index:1`. Poll order is by **(depth × weight) descending**. So when ingest has 100 and summarize has 50, effective priority is 400 vs 100 → workers prefer ingest. As ingest drains, summarize (and then score/index) get workers. Result: a nice E2E flow instead of “all workers on ingest” or “all on one queue”.

## How it works

- **Queues:** `ingest` → `normalize` → `summarize` → `score` → `index` (Redis lists).
- **When QUEUE_WORK_DIVISION is true:** Before each `blpop`, the worker fetches the current length of every queue (one Redis pipeline). It then orders queues by **(depth × stage_weight) descending** and polls in that order. Higher weight = more workers at that stage.
- **When false:** Fixed order (summarize, index, score, ingest, normalize) — downstream-first, no weighting.

## Configuration

| Env | Default | Description |
|-----|---------|-------------|
| **QUEUE_WORK_DIVISION** | `true` | When `true`, workers poll by weighted depth (earlier stages get more workers). When `false`, fixed order. |
| **QUEUE_STAGE_WEIGHTS** | `ingest:4,normalize:3,summarize:2,score:1,index:1` | Comma-separated `stage:weight`. Higher weight = more workers at that stage. |

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
- **Worker scale from UI:** The ops page has +/- buttons to change worker count. **POST /v1/admin/scale/workers** with `{"count": N}` stores the desired count in Redis. If **COMPOSE_PROJECT_DIR** is set to the path containing `docker-compose.yml` (and the API process can run `docker compose`), the API will run `docker compose up -d --scale worker=N` to apply. Otherwise, run manually: `docker compose up -d --scale worker=N`.
- **Worker id:** Each worker registers with a unique id (`WORKER_ID` env or `hostname-pid`). Scaled Docker Compose workers get distinct hostnames (e.g. `sentiment_api-worker-1`, `sentiment_api-worker-2`).
- **Prometheus:** `queue_depth{name="..."}` gauges are updated by the API when it serves `/metrics` (and by the daemon for ingest). Workers do not export metrics; they only consume using the dynamic order.

## Cost / performance

- One pipeline of `LLEN` per poll (5 keys). Overhead is small. No caching is used; order is recomputed every loop so it reacts quickly to queue growth.
