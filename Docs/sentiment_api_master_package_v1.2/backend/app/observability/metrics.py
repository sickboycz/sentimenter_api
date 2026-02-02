from __future__ import annotations

from prometheus_client import Counter, Histogram

REQUESTS_TOTAL = Counter(
    "sentiment_api_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "sentiment_api_http_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)
