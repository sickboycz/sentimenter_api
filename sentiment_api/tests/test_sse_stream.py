"""SSE stream tests (v1.2)."""
import pytest


@pytest.mark.skip(reason="TestClient.stream blocks on infinite SSE; run manually against live server")
def test_sse_stream_content_type(client, api_key):
    with client.stream("GET", "/v1/stream/events", headers={"X-API-Key": api_key}) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        chunk = next(r.iter_text())
        assert "event:" in chunk
        assert "data:" in chunk
