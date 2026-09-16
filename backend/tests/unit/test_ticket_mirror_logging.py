"""Proves the 2026-09-16 fix: every outcome of _mirror_to_real_api now logs
something explicit and greppable, instead of 4 of its 5 outcomes (3 skip
reasons + success) being completely silent — the only prior signal was a
generic real_ticket_id-is-null local ticket, indistinguishable from the
outside between "no auth_token", "no language_id", "category not mapped",
and "actually called the API and it worked". This mattered in practice:
diagnosing a real production failure took many rounds of live API testing
and direct DB queries specifically because pod logs showed nothing useful.
"""

import logging

from app.services import ticket_service


def _create_with_automation(db, account, **overrides):
    kwargs = dict(
        account_id=account.id, category="not_showing_face", sub_category="s",
        description="d", description_en="d",
    )
    kwargs.update(overrides)
    return ticket_service.create_ticket_with_automation(db, **kwargs)


def test_logs_skip_reason_when_no_auth_token(db, account, admin, caplog):
    with caplog.at_level(logging.INFO):
        _create_with_automation(db, account)
    assert "SKIPPED" in caplog.text
    assert "no auth_token" in caplog.text


def test_logs_skip_reason_when_no_language_id(db, account, admin, caplog):
    assert account.onboarded_language_id is None
    with caplog.at_level(logging.INFO):
        _create_with_automation(db, account, auth_token="t")  # no language_id anywhere
    assert "SKIPPED" in caplog.text
    assert "language_id" in caplog.text


def test_logs_skip_reason_when_category_unmapped(db, account, admin, caplog):
    with caplog.at_level(logging.INFO):
        _create_with_automation(db, account, category="account_blocked", auth_token="t", language_id=1)
    assert "SKIPPED" in caplog.text
    assert "account_blocked" in caplog.text
    assert "no confirmed issue_id" in caplog.text


def test_logs_success_with_real_ticket_id(db, account, admin, monkeypatch, caplog):
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: 2119)
    with caplog.at_level(logging.INFO):
        _create_with_automation(db, account, auth_token="t", language_id=1)
    assert "SUCCEEDED" in caplog.text
    assert "2119" in caplog.text


def test_logs_failure_with_status_and_body(db, account, admin, monkeypatch, caplog):
    from app.integrations import dostt_api_client

    def fake_create_ticket(**kwargs):
        raise dostt_api_client.DosttApiError(400, '{"message": {"issues": ["Invalid pk"]}}')

    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", fake_create_ticket)
    with caplog.at_level(logging.INFO):
        _create_with_automation(db, account, auth_token="t", language_id=1)
    assert "FAILED" in caplog.text
    assert "400" in caplog.text
    assert "Invalid pk" in caplog.text
