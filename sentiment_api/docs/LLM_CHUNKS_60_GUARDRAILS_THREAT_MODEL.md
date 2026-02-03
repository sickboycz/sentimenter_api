# Guardrails & Threat Model (v1.0)

## Prompt injection
- Treat input as untrusted.
- Output must match schema.
- Evidence refs only by id, no invented URLs.

## No hallucinated tickers
- Call C receives allowed_symbols; output validated against that list.
- Allocator rejects any unknown symbol and logs violation.

## Cost control
- Skip calls if impact_level < L2 or confidence < 0.25.
- Cache all steps.
- Cap allowed_symbols list to 600.

## Compliance
- Do not store full copyrighted text unless licensed.
- Store evidence snippets only.

