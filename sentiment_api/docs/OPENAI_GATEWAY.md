# OpenAI API: Responses API Primarily, No Chat Requests (Hard Law)

**Rule:** Use the **Responses API** primarily for text generation; **no Chat Completions** requests. Chunking and batching only.

## Gateway

All OpenAI API traffic goes through **`sentiment_api/llm/openai_gateway.py`**:

- **Text generation (Responses API only)**: `responses_text()` (single prompt → schema `{ text: string }`), `responses_text_batched()` (chunk long user content, one Responses API call per chunk, concatenate). **No Chat Completions.**
- **Translation**: `responses_structured()` with schema `{ translation: string }`; one call per chunk.
- **Embeddings**: `embeddings_batched()`, `embed_one()` (openai client; batched).
- **Structured JSON**: `responses_structured()` (name, schema, system_prompt, user_prompt).

This module is the **only** place that imports `openai` or calls the API (including `httpx` for the Responses endpoint).

## Callers

| Component | Uses |
|-----------|------|
| **translation.py** | `responses_structured()` with SCHEMA_TRANSLATION per chunk |
| **client.py** (`call_chat`) | `responses_text_batched()` — long user content chunked, one Responses API call per chunk |
| **embeddings.py** | `embed_one()`, `embeddings_batched()` |
| **api/main.py** (health) | `responses_text()` for a minimal validation call |
| **engines/llm_asset_targeting/openai_provider.py** | `responses_structured()` |

## Config

- **Chat**: `translation_chunk_chars`, `translation_batch_size`, `model_escalation`, `openai_base_url`
- **Embeddings**: `model_embedding_id`, `openai_base_url`; batch size and max chars in gateway defaults
- **Translation**: `model_translation`, `translation_chunk_chars`, `translation_batch_size`

## Adding New OpenAI Usage

Do **not** add new `from openai import OpenAI` or direct `client.chat.completions.create` / `client.embeddings.create` elsewhere. Add a batched/chunked entry point in `openai_gateway.py` and call it from your code.
