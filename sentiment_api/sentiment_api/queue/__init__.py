"""Redis-based job queue for ingestion pipeline."""

from sentiment_api.queue.client import get_queue, JobQueue

__all__ = ["get_queue", "JobQueue"]
