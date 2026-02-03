# Caching & Idempotency (v1.0)

Every step (A/B/C) is cached by deterministic hashes.

cache key inputs:
- cluster_id, cluster_version
- step (channel_infer|sector_map|ticker_select)
- model
- prompt_hash
- packet_hash
- schema_hash

cache_key = sha256(f"{cluster_id}:{cluster_version}:{step}:{model}:{prompt_hash}:{packet_hash}:{schema_hash}")

Rules:
- If cached status=ok: reuse
- If cached status=failed: retry only after backoff (10 min) and max 3 retries
- Add stampede protection with Redis lock (optional but recommended)

Determinism:
- temperature=0
- strict JSON schema
- bounded max output tokens

