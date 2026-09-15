"""Proves the 2026-09-11 fix: booting with ENVIRONMENT != "dev" while the
admin secret/password are still at their checked-into-the-repo defaults is
now impossible — see app/main.py, which calls this at import time.
"""

import pytest

from app.core.config import Settings, assert_admin_secrets_are_safe


def _settings(**overrides) -> Settings:
    return Settings(**overrides)


def test_dev_environment_is_never_blocked_regardless_of_secrets():
    s = _settings(ENVIRONMENT="dev", ADMIN_SESSION_SECRET="dev-only-change-me", ADMIN_PASSWORD="dosttSupport@123")
    assert_admin_secrets_are_safe(s)  # must not raise


def test_non_dev_with_default_secret_is_blocked():
    s = _settings(ENVIRONMENT="production", ADMIN_SESSION_SECRET="dev-only-change-me", ADMIN_PASSWORD="a-real-password")
    with pytest.raises(RuntimeError, match="ADMIN_SESSION_SECRET"):
        assert_admin_secrets_are_safe(s)


def test_non_dev_with_default_password_is_blocked():
    s = _settings(ENVIRONMENT="production", ADMIN_SESSION_SECRET="a-real-secret", ADMIN_PASSWORD="dosttSupport@123")
    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        assert_admin_secrets_are_safe(s)


def test_non_dev_with_both_rotated_is_allowed():
    s = _settings(ENVIRONMENT="production", ADMIN_SESSION_SECRET="a-real-secret", ADMIN_PASSWORD="a-real-password")
    assert_admin_secrets_are_safe(s)  # must not raise
