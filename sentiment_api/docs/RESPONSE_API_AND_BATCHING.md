# Response API and batching — confirmation

## Response API (streaming)

**Yes.** The API uses a **streaming response** for real-time events:

- **Endpoint:** `GET /v1/stream/events`
- **Format:** Server-Sent Events (SSE), `StreamingResponse`, `media_type="text/event-stream"`
- **Events:** `heartbeat`, `mood_updated`, `impacts_updated`, `topics_updated` (every ~15s)
- **Payload:** Each event is `event: <type>\ndata: <json>\n\n`

See `sentiment_api/api/main.py` (stream_events) and `sentiment_api/api/rate_limit.py` (SSE concurrency limit).

---

## Sending in batches

**Embeddings:** Yes — embeddings are sent in batches where applicable.

- **`llm/embeddings.py`:** `embed_texts(texts: list[str], ...)` calls OpenAI with `input=texts` in chunks of 100 (API supports up to 2048 per request). `embed_text(text)` remains for single-text callers (e.g. worker, RAG query).
- **`retrieval/provider.py`:** `RealEmbeddingProvider.embed_docs(texts)` uses the batch path: it calls `embed_texts(texts)` once (or in chunks internally) and returns vectors in the same order.

**Worker / RAG:** One article per job; embedding for that article is a single `embed_text` call. Advanced search and any path that embeds many docs use `embed_docs` → batch `embed_texts`.

---

## Summary

| Area              | Response API / streaming     | Batching                          |
|-------------------|------------------------------|-----------------------------------|
| SSE `/v1/stream/events` | Yes — `StreamingResponse`, SSE | N/A (streaming events)            |
| OpenAI embeddings | N/A                          | Yes — batch via `embed_texts` and `embed_docs` |
| OpenAI chat       | No (sync completions)        | No (one request per call)         |
