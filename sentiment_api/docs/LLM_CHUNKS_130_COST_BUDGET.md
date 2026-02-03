# Cost & Latency Budget (v1.0)

Each cluster triggers up to 3 model calls.

Control levers:
- Skip A/B/C if L1 or lower.
- Skip B/C if confidence < 0.25.
- Cache everything.

Token budgets (suggested):
- Call A: max 400 output tokens
- Call B: max 600 output tokens
- Call C: max 600 output tokens

Latency:
- A/B/C should finish within 2s each (p95) under normal conditions.
- If timeouts occur, mark cache failed and fall back to deterministic-only allocation for that run.

