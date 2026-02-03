# Test Matrix (v1.0)

Unit tests:
- cache key stability
- schema validation
- allowlist enforcement (no hallucinated tickers)
- sector conservation
- ticker bounds + sorting
- deterministic allocator reproducibility

Integration tests:
- pipeline run with stub LLM outputs
- cache hit skips provider
- debug endpoint includes required fields

Contract tests:
- endpoints return schema-compliant objects
- error model stable
