"""Ingestion pipeline: discover -> fetch -> normalize -> dedupe -> cluster."""

from sentiment_api.ingest.daemon import run_daemon
from sentiment_api.ingest.worker import run_worker

__all__ = ["run_daemon", "run_worker"]
