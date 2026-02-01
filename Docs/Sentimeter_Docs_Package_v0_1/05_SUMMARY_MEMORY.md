# 05_SUMMARY_MEMORY.md
## L1 Facts
entities, numbers, dates, claims + evidence pointers

## L2 Micro (strict JSON)
headline, topics, tone, key_claims<=3, why_it_matters<=2, uncertainty_flags, evidence_refs

## L3 Structured (strict JSON)
canonical_story, channels, affected_assets, horizon, confidence, what_changed

## L4 Delta
state_key, prev→new, change_direction, change_confidence

## Caching
dedupe_key = hash(object_id + text_hash + schema_version + model_id + prompt_version)
