def test_sse_stream_content_type(client, api_key):
    # We only validate headers; do not block waiting for data indefinitely.
    with client.stream("GET", "/v1/stream/events", headers={"X-API-Key": api_key}) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type","")
        # read a small chunk
        chunk = next(r.iter_text())
        assert "event:" in chunk
        assert "data:" in chunk
