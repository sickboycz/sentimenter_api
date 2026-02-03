"""SSE stream tests (v1.2)."""
import pytest


def test_sse_stream_content_type(client, api_key):
    """Stream sends one event when max_events=1; assert content-type and first chunk."""
    with client.stream(
        "GET", "/v1/stream/events",
        params={"max_events": 1},
        headers={"X-API-Key": api_key},
        timeout=5.0,
    ) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        chunk = next(r.iter_text(), None)
        assert chunk is not None
        assert "event:" in chunk
        assert "data:" in chunk
