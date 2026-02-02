"""In-memory metrics registry with Prometheus text exposition format."""

import threading
import time
from collections import defaultdict
from typing import Any

_lock = threading.Lock()
_ingestion_errors: dict[str, int] = defaultdict(int)
_ingestion_lag: dict[str, float] = {}  # source_id -> seconds since last success
_last_ingestion_success: dict[str, float] = {}  # source_id -> timestamp
_translation_failures: dict[str, int] = defaultdict(int)
_queue_depth: dict[str, int] = {}
_api_latency: list[tuple[str, float]] = []
_api_errors: dict[tuple[str, str], int] = defaultdict(int)
_api_requests_total: dict[tuple[str, str], int] = defaultdict(int)  # (route, status) -> count
_fetch_duration_seconds: list[tuple[str, float]] = []  # (source_id, duration)
_MAX_LATENCY_SAMPLES = 1000
_MAX_FETCH_SAMPLES = 500
_MAX_ERROR_SAMPLES = 10000


def ingestion_errors_total(source_id: str, inc: int = 1) -> None:
    with _lock:
        _ingestion_errors[source_id] += inc


def ingestion_lag_seconds(source_id: str, seconds: float | None = None) -> None:
    """Set lag explicitly, or call with None after success to record current time."""
    with _lock:
        if seconds is not None:
            _ingestion_lag[source_id] = seconds
        else:
            import time
            _last_ingestion_success[source_id] = time.time()
            _ingestion_lag[source_id] = 0.0


def translation_failures_total(source_id: str, inc: int = 1) -> None:
    with _lock:
        _translation_failures[source_id] += inc


def queue_depth(name: str, depth: int) -> None:
    with _lock:
        _queue_depth[name] = depth


def api_latency_ms(route: str, ms: float) -> None:
    with _lock:
        _api_latency.append((route, ms))
        if len(_api_latency) > _MAX_LATENCY_SAMPLES:
            _api_latency.pop(0)


def fetch_duration_seconds(source_id: str, seconds: float) -> None:
    with _lock:
        _fetch_duration_seconds.append((source_id, seconds))
        if len(_fetch_duration_seconds) > _MAX_FETCH_SAMPLES:
            _fetch_duration_seconds.pop(0)


def api_errors_total(route: str, code: str, inc: int = 1) -> None:
    with _lock:
        key = (route, code)
        _api_errors[key] += inc
        if sum(_api_errors.values()) > _MAX_ERROR_SAMPLES:
            _api_errors.clear()


def api_requests_total(route: str, status: str, inc: int = 1) -> None:
    """Increment request counter for Prometheus rate() queries."""
    with _lock:
        key = (route, status)
        _api_requests_total[key] += inc
        if sum(_api_requests_total.values()) > _MAX_ERROR_SAMPLES:
            _api_requests_total.clear()


def collect_metrics() -> str:
    """Produce Prometheus text exposition format."""
    parts = []
    with _lock:
        if _ingestion_errors:
            parts.append("# TYPE ingestion_errors_total counter")
            for sid, v in _ingestion_errors.items():
                parts.append(f'ingestion_errors_total{{source_id="{_esc(sid)}"}} {v}')
        now = time.time()
        lag_sids = set(_ingestion_lag) | set(_last_ingestion_success)
        if lag_sids:
            parts.append("# TYPE ingestion_lag_seconds gauge")
            for sid in lag_sids:
                lag = now - _last_ingestion_success[sid] if sid in _last_ingestion_success else _ingestion_lag.get(sid, 0)
                parts.append(f'ingestion_lag_seconds{{source_id="{_esc(sid)}"}} {lag:.1f}')
        if _translation_failures:
            parts.append("# TYPE translation_failures_total counter")
            for sid, v in _translation_failures.items():
                parts.append(f'translation_failures_total{{source_id="{_esc(sid)}"}} {v}')
        if _queue_depth:
            parts.append("# TYPE queue_depth gauge")
            for name, v in _queue_depth.items():
                parts.append(f'queue_depth{{name="{_esc(name)}"}} {v}')
        if _api_latency:
            parts.append("# TYPE api_latency_ms_avg gauge")
            by_route: dict[str, list[float]] = defaultdict(list)
            for r, ms in _api_latency:
                by_route[r].append(ms)
            for r, vals in by_route.items():
                avg = sum(vals) / len(vals)
                parts.append(f'api_latency_ms_avg{{route="{_esc(r)}"}} {avg:.2f}')
        if _api_errors:
            parts.append("# TYPE api_errors_total counter")
            for (route, code), v in _api_errors.items():
                parts.append(f'api_errors_total{{route="{_esc(route)}",code="{_esc(code)}"}} {v}')
        if _api_requests_total:
            parts.append("# TYPE api_requests_total counter")
            for (route, status), v in _api_requests_total.items():
                parts.append(f'api_requests_total{{route="{_esc(route)}",status="{_esc(status)}"}} {v}')
        if _fetch_duration_seconds:
            parts.append("# TYPE fetch_duration_seconds gauge")
            by_src: dict[str, list[float]] = defaultdict(list)
            for sid, sec in _fetch_duration_seconds:
                by_src[sid].append(sec)
            for sid, vals in by_src.items():
                p95_idx = int(len(vals) * 0.95) or 0
                p95 = sorted(vals)[p95_idx] if vals else 0
                parts.append(f'fetch_duration_seconds_p95{{source_id="{_esc(sid)}"}} {p95:.2f}')
    return "\n".join(parts) + "\n" if parts else "# No metrics yet\n"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
