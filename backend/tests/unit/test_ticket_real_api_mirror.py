"""Proves the real-API mirror in ticket_service._mirror_to_real_api: opt-in
only when auth_token/language_id/a confirmed issue_id are all present, never
blocking or failing the local ticket write, and falls back cleanly whenever
any piece is missing — see app/data/issue_catalog.py and
app/integrations/dostt_api_client.py for what's actually confirmed.
"""

import base64
import json
from types import SimpleNamespace

from app.integrations import dostt_api_client
from app.services import attachment_service, chat_session_service, ticket_service


def _fake_token(user_type=1, country="US", onboarded_language_id=7) -> str:
    def b64(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    payload = {"user_payload": {"user_type": user_type, "country": country, "onboarded_language_id": onboarded_language_id}}
    return f"{b64({'alg': 'HS256'})}.{b64(payload)}.sig"


def _create_with_automation(db, account, monkeypatch=None, **overrides):
    kwargs = dict(
        account_id=account.id, category="charged_incorrectly", sub_category="extra coins",
        description="d", description_en="d",
    )
    kwargs.update(overrides)
    return ticket_service.create_ticket_with_automation(db, **kwargs)


def test_no_auth_token_skips_real_api_entirely(db, account, admin, monkeypatch):
    called = []
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: called.append(kw) or 999)

    ticket = _create_with_automation(db, account)

    assert not called
    assert ticket.real_ticket_id is None


def test_confirmed_category_with_auth_token_calls_real_api(db, account, admin, monkeypatch):
    captured = {}

    def fake_create_ticket(**kwargs):
        captured.update(kwargs)
        return 2119

    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", fake_create_ticket)

    ticket = _create_with_automation(
        db, account,
        auth_token="tok123", language_id=1, callback_requested=True,
    )

    assert ticket.real_ticket_id == 2119
    assert captured["auth_token"] == "tok123"
    assert captured["language_id"] == 1
    assert captured["issue_id"] == 361  # charged_incorrectly, confirmed 2026-09-08
    assert captured["is_call_opted_in"] is True
    assert captured["description"] == "d"


def test_user_type_code_falls_back_to_account_role_when_not_given(db, account, listener_account, admin, monkeypatch):
    captured = {}
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: captured.update(kw) or 1)

    _create_with_automation(db, account, auth_token="t", language_id=1)
    assert captured["user_type"] == 0  # AccountRole.USER -> 0, confirmed

    captured.clear()
    _create_with_automation(db, listener_account, auth_token="t", language_id=1)
    assert captured["user_type"] == 1  # AccountRole.LISTENER -> 1, unconfirmed best-guess mapping


def test_explicit_user_type_code_overrides_role_fallback(db, account, admin, monkeypatch):
    captured = {}
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: captured.update(kw) or 1)

    _create_with_automation(db, account, auth_token="t", language_id=1, user_type_code=7)
    assert captured["user_type"] == 7


def test_language_id_falls_back_to_account_onboarded_language_id(db, account, admin, monkeypatch):
    account.onboarded_language_id = 3
    db.commit()
    captured = {}
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: captured.update(kw) or 1)

    _create_with_automation(db, account, auth_token="t")  # no language_id passed explicitly

    assert captured["language_id"] == 3


def test_no_language_id_from_any_source_skips_real_api(db, account, admin, monkeypatch):
    assert account.onboarded_language_id is None
    called = []
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: called.append(kw) or 1)

    ticket = _create_with_automation(db, account, auth_token="t")  # no language_id anywhere

    assert not called
    assert ticket.real_ticket_id is None


def test_explicit_language_id_overrides_account_fallback(db, account, admin, monkeypatch):
    account.onboarded_language_id = 3
    db.commit()
    captured = {}
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: captured.update(kw) or 1)

    _create_with_automation(db, account, auth_token="t", language_id=9)

    assert captured["language_id"] == 9


def test_unmapped_category_skips_real_api(db, account, admin, monkeypatch):
    called = []
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: called.append(kw) or 1)

    # account_blocked has no exact-match entry in the real issue catalog at
    # all (see app/data/issue_catalog.py) — unlike negative_balance, which
    # used to be the example here until it got a confirmed real issue_id.
    ticket = _create_with_automation(db, account, category="account_blocked", auth_token="t", language_id=1)

    assert not called
    assert ticket.real_ticket_id is None


def test_country_code_falls_back_to_token_claim_not_hardcoded_in(db, account, admin, monkeypatch):
    captured = {}
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: captured.update(kw) or 1)

    _create_with_automation(db, account, auth_token=_fake_token(country="US"), language_id=1)

    assert captured["country_code"] == "US"


def test_country_code_defaults_to_in_when_token_has_no_claim(db, account, admin, monkeypatch):
    captured = {}
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: captured.update(kw) or 1)

    _create_with_automation(db, account, auth_token="not-a-real-jwt", language_id=1)

    assert captured["country_code"] == "IN"


def test_explicit_country_code_overrides_token_claim(db, account, admin, monkeypatch):
    captured = {}
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: captured.update(kw) or 1)

    _create_with_automation(db, account, auth_token=_fake_token(country="US"), language_id=1, country_code="GB")

    assert captured["country_code"] == "GB"


def test_language_id_falls_back_to_token_claim_when_account_has_none(db, account, admin, monkeypatch):
    account.onboarded_language_id = None
    db.commit()
    captured = {}
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: captured.update(kw) or 1)

    _create_with_automation(db, account, auth_token=_fake_token(onboarded_language_id=9))

    assert captured["language_id"] == 9


def test_user_type_falls_back_to_token_claim_when_no_account(db, account, admin, monkeypatch):
    # Exercises _mirror_to_real_api directly with account=None — the
    # branch USER_TYPE_CODE_BY_ROLE.get(account.role, 0) can never reach,
    # since that lookup always has its own 0 default once an account
    # exists. account=None only happens when the account lookup itself
    # failed (e.g. account_for_language is None in create_ticket_with_
    # automation), which isn't reachable through the public function
    # without violating the tickets.account_id FK — so this goes straight
    # at the private function instead.
    captured = {}
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: captured.update(kw) or 1)
    ticket = ticket_service.create_ticket(
        db, account_id=account.id, category="charged_incorrectly", sub_category="s",
        description="d", description_en="d", preferred_language="en",
    )

    ticket_service._mirror_to_real_api(
        db, ticket,
        account=None,
        auth_token=_fake_token(user_type=1),
        language_id=1,
        user_type_code=None,
        country_code=None,
        attachment=None,
    )

    assert captured["user_type"] == 1


def test_app_version_flows_through_to_the_real_api_call(db, account, admin, monkeypatch):
    captured = {}
    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", lambda **kw: captured.update(kw) or 1)

    _create_with_automation(db, account, auth_token="tok", language_id=1, app_version="1.1.38")

    assert captured["app_version"] == "1.1.38"


def test_pending_attachment_gets_attached_to_ticket_and_passed_to_mirror(db, account, admin, monkeypatch):
    session = chat_session_service.start_session(db, account.id, "en")
    fake_upload = SimpleNamespace(content_type="image/png", filename="shot.png")
    attachment_service.save_pending_attachment(db, session.id, fake_upload, b"fake-bytes")

    captured = {}
    monkeypatch.setattr(
        ticket_service.dostt_api_client, "create_ticket",
        lambda **kw: captured.update(kw) or 5,
    )

    ticket = _create_with_automation(
        db, account, auth_token="t", language_id=1, session_id=session.id,
    )

    assert ticket.attachment_path is not None
    assert captured["image_path"] == ticket.attachment_path
    assert captured["image_content_type"] == "image/png"
    # consumed — a second ticket in the same session shouldn't reuse it
    assert attachment_service.get_pending_attachment(db, session.id) is None


def test_no_pending_attachment_passes_none_image_path(db, account, admin, monkeypatch):
    session = chat_session_service.start_session(db, account.id, "en")
    captured = {}
    monkeypatch.setattr(
        ticket_service.dostt_api_client, "create_ticket",
        lambda **kw: captured.update(kw) or 5,
    )

    ticket = _create_with_automation(db, account, auth_token="t", language_id=1, session_id=session.id)

    assert ticket.attachment_path is None
    assert captured["image_path"] is None


def test_real_api_failure_does_not_break_local_ticket(db, account, admin, monkeypatch):
    def fake_create_ticket(**kwargs):
        raise dostt_api_client.DosttApiError(400, '{"message": {"issues": ["Invalid pk"]}}')

    monkeypatch.setattr(ticket_service.dostt_api_client, "create_ticket", fake_create_ticket)

    ticket = _create_with_automation(db, account, auth_token="t", language_id=1)

    assert ticket.real_ticket_id is None
    assert ticket.id is not None  # local ticket still created and committed fine
