"""Rate limiting (v1.2) — 60 req/min default, 429 when exceeded."""


def test_rate_limiting_returns_429(client):
    """After exceeding 60 req/min, expect 429. Use isolated key to avoid affecting other tests."""
    key = "rate_limit_test_key_12345678901234"  # Must be in SENTIMENT_API_API_KEYS
    responses = []
    for _ in range(65):
        r = client.get("/v1/mood/now", headers={"X-API-Key": key})
        responses.append(r.status_code)
    assert 429 in responses
