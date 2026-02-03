# Work division by queue depth

Workers divide work based on **growing queues**: they prefer the fullest queue when polling, so the busiest stage is drained first.

## How it works

- **Queues:** `ingest` → `normalize` → `summarize` → `score` → `index` (Redis lists).
- **Default:** Before each `blpop`, the worker fetches the current length of every queue (one Redis pipeline). It then polls in **descending order of length** (fullest first). Ties are broken by a fixed priority: summarize, index, score, ingest, normalize.
- **Effect:** When the summarize queue grows (e.g. after a burst of ingest), all workers naturally prefer summarize until it shrinks. Same for any other queue that backs up.

## Configuration

| Env | Default | Description |
|-----|---------|-------------|
| **QUEUE_WORK_DIVISION** | `true` | When `true`, workers poll queues in order of current depth (fullest first). When `false`, they use a fixed order (summarize, index, score, ingest, normalize). |

To use the fixed order (previous behaviour):

```bash
SENTIMENT_API_QUEUE_WORK_DIVISION=false
```

## Ops

- **GET /v1/admin/ops** returns `queues` (depth per queue), `queues_total`, and **`workers`**: a list of worker instances with `id`, `last_seen`, `age_sec`, `last_job` (queue + at), and `counts` (per-queue job counts). Use the ops page **Workers** card to see the worker list and work assignment.
- **Worker id:** Each worker registers with a unique id (`WORKER_ID` env or `hostname-pid`). Scaled Docker Compose workers get distinct hostnames (e.g. `sentiment_api-worker-1`, `sentiment_api-worker-2`).
- **Prometheus:** `queue_depth{name="..."}` gauges are updated by the API when it serves `/metrics` (and by the daemon for ingest). Workers do not export metrics; they only consume using the dynamic order.

## Cost / performance

- One pipeline of `LLEN` per poll (5 keys). Overhead is small. No caching is used; order is recomputed every loop so it reacts quickly to queue growth.
