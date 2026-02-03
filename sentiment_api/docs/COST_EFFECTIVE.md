# Cost-effective defaults

The stack is tuned for **lowest cost** by default. You can trade cost for quality by changing a few settings.

**Applied with:** cost-effective mode, **response API (SSE)** at `GET /v1/stream/events`, and **embedding batching** — see `docs/RESPONSE_API_AND_BATCHING.md`.

---

## What’s cost-effective by default

| Setting | Default (cost-effective) | Effect |
|--------|---------------------------|--------|
| **COST_EFFECTIVE** | `true` | Use 384-dim embeddings, mini-only LLM, skip LLM asset targeting |
| **model_embedding_id** | `openai:text-embedding-3-small:384` | 384-dim embeddings (cheaper than 768) |
| **model_escalation** | `gpt-5-mini` only | No fallback to gpt-5.2 / 5.2-pro (fewer tokens) |
| **Asset targeting** | Rule-based only | No extra LLM call per cluster for winners/losers |
| **Cluster limit (worker)** | 200 | Fewer cluster vectors loaded for similarity (faster, less memory) |
| **Embedding batch size** | 256 | Fewer OpenAI requests when embedding many texts |
| **CLUSTER_SIMILARITY_THRESHOLD** | `0.88` | Topic clustering (same story, different wording); use 0.95+ for dedup only |
| **QUEUE_WORK_DIVISION** | `true` | Workers poll fullest queue first; see `docs/WORK_DIVISION.md` |

---

## Optional: higher quality (higher cost)

Set in `.env`:

```bash
# Prefer quality over cost
SENTIMENT_API_COST_EFFECTIVE=false
SENTIMENT_API_MODEL_EMBEDDING_ID=openai:text-embedding-3-small:768
SENTIMENT_API_MODEL_ESCALATION=gpt-5-mini,gpt-5.2,gpt-5.2-pro
```

- **COST_EFFECTIVE=false** re-enables LLM-based asset targeting (one extra LLM call per L2+ cluster).
- **768-dim embeddings** improve retrieval/clustering quality at higher token cost.
- **Escalation** adds fallback to stronger models when mini fails (more tokens on failure).

---

## Other levers

- **Retrieval (2-tier):** Tier A uses 384-dim by default; Tier B uses 768. For cost-only, use 384 for both (`RETRIEVAL_TIERB_MODEL_ID=openai:text-embedding-3-small:384`).
- **Daemon interval:** Longer `update_interval_sec` in the source registry = fewer ingest cycles and fewer articles/minute.
- **Worker replicas:** Fewer workers = less parallel LLM/embedding load (set `WORKER_REPLICAS=1` or `2` in `.env`).
- **Work division:** With `QUEUE_WORK_DIVISION=true` (default), workers prefer the fullest queue so backlogs drain faster; see `docs/WORK_DIVISION.md`.
- **Frontend refetch:** Increase refetch intervals in the frontend hooks to reduce API calls from the dashboard.
