"""Proves the 2026-09-15 fix: staging and production have completely
different issue_id numbering for the same category (confirmed empirically
by pulling both real catalogs and diffing them — e.g. "Not Getting Calls"
is id 43 on staging, id 363 on production), so issue_id_for() must pick the
right catalog based on which DOSTT_API_BASE_URL is actually configured,
never a single flat mapping.
"""

from app.core.config import settings
from app.data.issue_catalog import issue_id_for


def test_staging_base_url_uses_staging_catalog(monkeypatch):
    monkeypatch.setattr(settings, "DOSTT_API_BASE_URL", "https://testdostt.getlokalapp.com")
    assert issue_id_for("not_getting_calls") == 43


def test_non_staging_base_url_uses_production_catalog(monkeypatch):
    monkeypatch.setattr(settings, "DOSTT_API_BASE_URL", "https://api.getlokalapp.com")
    assert issue_id_for("not_getting_calls") == 363


def test_category_only_mapped_in_production_is_none_on_staging(monkeypatch):
    monkeypatch.setattr(settings, "DOSTT_API_BASE_URL", "https://testdostt.getlokalapp.com")
    assert issue_id_for("charged_incorrectly") is None  # production-only


def test_category_only_mapped_in_staging_would_differ_in_production(monkeypatch):
    monkeypatch.setattr(settings, "DOSTT_API_BASE_URL", "https://testdostt.getlokalapp.com")
    assert issue_id_for("cannot_hear") == 106  # staging value
    monkeypatch.setattr(settings, "DOSTT_API_BASE_URL", "https://api.getlokalapp.com")
    assert issue_id_for("cannot_hear") == 463  # production value — different id, same category
