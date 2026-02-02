"""Circuit breaker per source (AC-M1.3). Skips source after N consecutive failures."""

import logging
import threading
import time
from typing import Any

logger = logging.getLogger("sentiment_api.collectors.circuit_breaker")

FAILURE_THRESHOLD = 5
COOLDOWN_SEC = 300  # 5 minutes
_state: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def record_success(source_id: str) -> None:
    """Reset failure count on success."""
    with _lock:
        if source_id in _state:
            _state[source_id]["failures"] = 0
            _state[source_id]["last_failure_at"] = None


def record_failure(source_id: str) -> None:
    """Increment failure count."""
    with _lock:
        if source_id not in _state:
            _state[source_id] = {"failures": 0, "last_failure_at": None}
        _state[source_id]["failures"] = _state[source_id].get("failures", 0) + 1
        _state[source_id]["last_failure_at"] = time.time()


def is_open(source_id: str) -> bool:
    """True if circuit is open (source should be skipped)."""
    with _lock:
        s = _state.get(source_id)
        if not s or s.get("failures", 0) < FAILURE_THRESHOLD:
            return False
        last = s.get("last_failure_at") or 0
        if time.time() - last > COOLDOWN_SEC:
            s["failures"] = 0
            return False
        return True
