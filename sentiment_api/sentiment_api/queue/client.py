"""Redis queue client."""

import json
import logging
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger("sentiment_api.queue")

QUEUE_INGEST = "sentiment_api:ingest"
QUEUE_NORMALIZE = "sentiment_api:normalize"
QUEUE_SUMMARIZE = "sentiment_api:summarize"
QUEUE_SCORE = "sentiment_api:score"
QUEUE_INDEX = "sentiment_api:index"

_default_client: redis.Redis | None = None


async def get_queue(redis_url: str) -> redis.Redis:
    global _default_client
    if _default_client is None:
        _default_client = redis.from_url(redis_url, decode_responses=True)
    return _default_client


class JobQueue:
    """Simple FIFO job queue over Redis list."""

    def __init__(self, client: redis.Redis, queue_name: str):
        self.client = client
        self.queue_name = queue_name

    async def push(self, payload: dict[str, Any]) -> None:
        await self.client.rpush(self.queue_name, json.dumps(payload))

    async def pop(self, timeout_sec: float = 0) -> dict[str, Any] | None:
        result = await self.client.blpop(self.queue_name, timeout=timeout_sec)
        if result:
            _, data = result
            return json.loads(data)
        return None

    async def length(self) -> int:
        return await self.client.llen(self.queue_name)
