"""Prometheus metrics (AC-M10.1, M10.2, M10.3)."""

from sentiment_api.metrics.registry import (
    ingestion_errors_total,
    ingestion_lag_seconds,
    translation_failures_total,
    queue_depth,
    api_latency_ms,
    api_errors_total,
    api_requests_total,
    fetch_duration_seconds,
    collect_metrics,
)

__all__ = [
    "ingestion_errors_total",
    "ingestion_lag_seconds",
    "translation_failures_total",
    "queue_depth",
    "api_latency_ms",
    "api_errors_total",
    "api_requests_total",
    "collect_metrics",
]
