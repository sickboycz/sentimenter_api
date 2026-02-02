def test_missing_api_key_returns_enveloped_error(client):
    r = client.get("/v1/mood/now")
    assert r.status_code == 401
    body = r.json()
    assert "meta" in body and "errors" in body
    assert body["errors"][0]["code"] == "auth_missing_api_key"
