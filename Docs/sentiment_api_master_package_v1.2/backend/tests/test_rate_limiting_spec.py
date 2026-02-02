import pytest

@pytest.mark.skip(reason="Rate limiting not implemented in scaffold; implement middleware then enable this test.")
def test_rate_limiting_returns_429(client, api_key):
    for _ in range(200):
        client.get("/v1/mood/now", headers={"X-API-Key": api_key})
    # Expect 429 at some point
    assert False
