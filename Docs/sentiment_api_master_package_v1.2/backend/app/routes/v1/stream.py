from __future__ import annotations

import json
import time
from typing import Iterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ...deps import require_api_key
from ...utils.time import now_utc

router = APIRouter(prefix="/v1", tags=["stream"])

def _sse_event(event: str, data: dict) -> str:
    # SSE format: event: <name>\ndata: <json>\n\n
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"

def _generator(request_id: str) -> Iterator[str]:
    # Placeholder: real implementation subscribes to Redis/pubsub or DB notifications.
    while True:
        yield _sse_event("heartbeat", {"type":"heartbeat","ts": now_utc().isoformat(), "payload": {}, "request_id": request_id})
        time.sleep(15)

@router.get("/stream/events")
def stream_events(request: Request, _api_key: str = Depends(require_api_key)):
    return StreamingResponse(_generator(request.state.request_id), media_type="text/event-stream")
