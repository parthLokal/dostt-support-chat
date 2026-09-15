"""Proves the 2026-09-11 fix: /api/chat and /api/session/init had zero
throttling despite /api/chat calling a paid Gemini API on every request —
see app/core/rate_limit.py for why this is an in-memory fixed-window
limiter rather than Redis-backed.
"""

import pytest

from app.core.rate_limit import RateLimitedError, check_rate_limit


def test_allows_calls_under_the_limit():
    for _ in range(5):
        check_rate_limit("test_scope", "key-a", limit=5)  # must not raise


def test_blocks_the_call_that_exceeds_the_limit():
    for _ in range(5):
        check_rate_limit("test_scope", "key-b", limit=5)
    with pytest.raises(RateLimitedError):
        check_rate_limit("test_scope", "key-b", limit=5)


def test_different_keys_are_independent():
    for _ in range(5):
        check_rate_limit("test_scope", "key-c", limit=5)
    check_rate_limit("test_scope", "key-d", limit=5)  # a different key, must not raise


def test_different_scopes_are_independent():
    for _ in range(5):
        check_rate_limit("scope_one", "same-key", limit=5)
    check_rate_limit("scope_two", "same-key", limit=5)  # different scope, must not raise
