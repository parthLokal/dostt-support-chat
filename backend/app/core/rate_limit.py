"""In-memory rate limiter for endpoints that call paid/costly integrations
(/api/chat calls Gemini on every request) — a single-process, fixed-window
counter, not Redis-backed, because the app currently runs as one uvicorn
process (docker-compose.yml has no backend service or multi-worker config
yet). If this ever runs as multiple workers/instances, this needs to move
to a shared store instead — each process would otherwise track its own
separate counts and the real limit would silently become
(limit * process_count).

Deliberately simple (fixed window, not sliding-window/token-bucket) — good
enough to stop a tight retry loop or deliberate spam from hammering a paid
API with zero limit, which is the actual risk this closes, not perfectly
fair behavior at the window boundary.
"""

import threading
import time
from collections import defaultdict

from app.core.errors import AppError


class RateLimitedError(AppError):
    def __init__(self, message: str = "Too many requests — please slow down and try again in a moment.") -> None:
        super().__init__(message, status_code=429)


_lock = threading.Lock()
_counts: dict[tuple[str, str, int], int] = defaultdict(int)
_last_cleanup = time.monotonic()
_CLEANUP_INTERVAL_SEC = 300


def _cleanup_if_due(current_window: int) -> None:
    global _last_cleanup
    now = time.monotonic()
    if now - _last_cleanup < _CLEANUP_INTERVAL_SEC:
        return
    _last_cleanup = now
    stale_keys = [k for k in _counts if k[2] < current_window]
    for k in stale_keys:
        del _counts[k]


def check_rate_limit(scope: str, key: str, *, limit: int, window_seconds: int = 60) -> None:
    """Raises RateLimitedError once `key` has made more than `limit` calls
    under `scope` within the current fixed window. Call this before doing
    the expensive work (before the Gemini call), not after."""
    window = int(time.time() // window_seconds)
    count_key = (scope, key, window)
    with _lock:
        _cleanup_if_due(window)
        _counts[count_key] += 1
        current = _counts[count_key]
    if current > limit:
        raise RateLimitedError()


def reset_for_tests() -> None:
    """Test-only: clears all counters so one test's calls never bleed into
    another's — see tests/conftest.py's autouse fixture. Without this, the
    per-IP counter especially (every TestClient request shares the same
    fake client IP) would accumulate across the whole test run."""
    with _lock:
        _counts.clear()


def client_ip(request) -> str:
    # No proxy/load-balancer in front of this yet (see docker-compose.yml —
    # Postgres only, no reverse proxy), so request.client.host is the real
    # client IP for now. Once this sits behind one, this needs to read
    # X-Forwarded-For instead (and only trust it from the proxy itself).
    return request.client.host if request.client else "unknown"
