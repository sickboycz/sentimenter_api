# Implementation Steps (v1.0)

Follow this order exactly:

1) Add Pydantic schemas + JSON schema files (Calls A/B/C)
2) Add packet builder + packet hashing
3) Add OpenAI Responses provider wrapper
4) Add DB cache store + migrations
5) Add candidate generator + security master lookups
6) Add deterministic allocator + conservation rules
7) Add allocation persistence + ledger writes
8) Add debug endpoint
9) Add tests and enforce invariants
10) Add calibration job (forward only)

