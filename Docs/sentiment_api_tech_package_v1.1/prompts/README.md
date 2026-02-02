# Prompt Contracts (Schema-Locked) — sentiment_api v1.0

Purpose: ensure outputs are *structured, auditable, and stable*.

Rules:
1. **JSON only** (no extra text).
2. Must validate against schema.
3. Must include citations / evidence pointers.
4. No speculation: if unknown, write `null` and add an `uncertainty_flags[]` entry.

Files:
- `L1_fact_extraction.md`
- `L2_article_micro.md`
- `L3_cluster_summary.md`
- `L4_state_delta.md`
- `impact_scoring.md`

