# Cluster Packet (v1.0) — Deterministic LLM Input

The packet builder is deterministic and the only allowed LLM input.

## Packet fields
- headline_en
- summary_bullets_en (max 12)
- topics, regions
- impact_score, impact_level, expected_direction, confidence
- evidence[]: up to 6 snippets, each ≤ 420 chars, total ≤ 2400 chars
- direct_mentions[]: mapped tickers (optional)
- numeric_facts[]: extracted numbers like bps, %, etc (optional)

## Evidence selection rule (deterministic)
Sort evidence rows by:
- relevance_score desc
- url asc (tie-break)
Then take top N under caps.

## Hashing
- packet_hash = sha256(canonical_json(packet))
where canonical json is:
- sorted keys
- stable array order
- no runtime timestamps beyond stored cluster timestamps

packet_hash participates in cache keys so packet drift is detectable.

