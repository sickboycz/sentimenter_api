"""Shared HTTP client with retries and backoff for 429/5xx (AC-M1.3)."""

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("sentiment_api.collectors.http")

# Retry config
MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 60.0


def fetch_with_retry(
    url: str,
    *,
    method: str = "GET",
    params: dict | None = None,
    timeout: float = 20.0,
    follow_redirects: bool = True,
) -> httpx.Response:
    """Fetch URL with retries and exponential backoff on 429/5xx (AC-M1.3)."""
    last_exc: Exception | None = None
    backoff = INITIAL_BACKOFF
    with httpx.Client(timeout=timeout, follow_redirects=follow_redirects) as client:
        for attempt in range(MAX_RETRIES):
            try:
                if method.upper() == "GET":
                    resp = client.get(url, params=params or {})
                else:
                    resp = client.request(method, url, params=params or {})
                if resp.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "HTTP %s from %s (attempt %d/%d), backing off %.1fs",
                        resp.status_code, url[:80], attempt + 1, MAX_RETRIES, backoff,
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in RETRY_STATUS_CODES or attempt >= MAX_RETRIES - 1:
                    raise
                last_exc = e
                logger.warning("HTTP %s (attempt %d/%d), backing off %.1fs", e.response.status_code, attempt + 1, MAX_RETRIES, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
            except (httpx.HTTPError, OSError) as e:
                last_exc = e
                if attempt >= MAX_RETRIES - 1:
                    raise
                logger.warning("Fetch failed %s (attempt %d/%d): %s, backing off %.1fs", url[:80], attempt + 1, MAX_RETRIES, e, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
    if last_exc:
        raise last_exc
    raise RuntimeError("fetch_with_retry exhausted")
