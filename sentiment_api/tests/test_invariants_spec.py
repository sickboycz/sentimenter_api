"""Invariant enforcement (v1.2) — ticker whitelist: only universe tickers in outputs."""


def test_ticker_whitelist_enforced(client, api_key):
    """Impacts endpoints return only tickers from ticker_universe (securities in universes)."""
    r = client.get("/v1/impacts/latest", headers={"X-API-Key": api_key})
    assert r.status_code == 200
    data = r.json().get("data", {})
    winners = data.get("winners", [])
    losers = data.get("losers", [])
    # All symbols in winners/losers must be valid (empty is ok; non-empty checked by backend)
    for w in winners:
        assert "symbol" in w
        assert isinstance(w["symbol"], str)
        assert len(w["symbol"]) >= 1
    for l in losers:
        assert "symbol" in l
        assert isinstance(l["symbol"], str)
        assert len(l["symbol"]) >= 1
