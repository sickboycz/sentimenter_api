# Diagnostics & Debug (v1.0)

The debug endpoint is mandatory because it prevents “mystery math”.

Debug payload must include:
- packet (sanitized)
- packet_hash, prompt_hashes, schema_hashes, cache_keys
- cache entries status for A/B/C
- channel vector numeric values (c_k)
- market raw scores and final scores
- sector raw scores and post-conservation scores
- ticker candidates:
  - count by source (mentions/sector/ruleset)
  - final list length and truncation reason
- top winners/losers with:
  - signed_score
  - expected_return_bps
  - confidence
  - drivers and evidence_ids
- invariant violations list

Provide a single JSON response for easy logging/export.

