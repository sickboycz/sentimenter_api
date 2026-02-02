# sentiment_api — Requirements

**Source of truth:** `pyproject.toml`  
**Lock file:** `uv.lock` (when using uv)

## Python

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| fastapi | ≥0.109.0 |
| uvicorn | ≥0.27.0 |
| asyncpg | ≥0.29.0 |
| redis | ≥5.0.0 |
| pyyaml | ≥6.0 |
| jsonschema | ≥4.20.0 |
| httpx | ≥0.26.0 |
| pydantic | ≥2.5.0 |
| pydantic-settings | ≥2.1.0 |
| feedparser | ≥6.0.0 |
| trafilatura | ≥6.0.0 |
| langdetect | ≥1.0.9 |
| openai | ≥1.12.0 |
| numpy | ≥1.24.0 |
| argon2-cffi | ≥23.1.0 |
| sentence-transformers | ≥2.2.0 |
| weaviate-client | ≥4.0.0 |

**Dev:** pytest ≥7.4.0, pytest-asyncio ≥0.23.0

**Optional vector backends** (see `docs/PINECONE_WEAVIATE_INTEGRATION.md`): `[vector-pinecone]` / `[vector-weaviate]` extras in `pyproject.toml`. Weaviate is included by default for 2-tier retrieval and external vector search.

## Frontend (Node.js)

| Requirement | Version |
|-------------|---------|
| Node.js | 18+ |
| next | 14.1.0 |
| react | 18.2.0 |
| @tanstack/react-query | 5.18.1 |
| zod | 3.23.8 |
| recharts | 2.12.0 |

**Dev:** vitest, playwright, @testing-library/react, typescript

## Regenerating requirements.txt

```bash
uv export --no-dev -o requirements.txt
uv export --extra dev -o requirements-dev.txt
```
