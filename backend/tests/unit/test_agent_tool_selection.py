"""Proves the security boundary in agent/executor.py: whatever account_id a
tool call claims, the handler only ever sees ctx.account_id. This is the
same class of test the AstroHelp sibling project runs for astrologer_id —
worth keeping even though this file doesn't cover the full tool-calling loop
(that needs a real/faked Gemini response), because this is the one property
that must never regress silently.
"""

from app.agent import executor
from app.agent.context import SessionContext


def _ctx(db, account_id: int = 1, ticket_count: int = 0) -> SessionContext:
    return SessionContext(
        account_id=account_id, name="Priya", role="user", language="en",
        db=db, session_id="s1", ticket_count_this_session=ticket_count,
    )


def test_account_id_in_tool_input_is_ignored_and_overridden(db, account, call):
    """A malicious/confused tool call claims account_id=9999 — the executor
    must still resolve everything against the real, authenticated account
    (ctx.account_id), never the value the model supplied."""
    malicious_input = {
        "account_id": 9999,
        "category": "charged_incorrectly",
        "sub_category": "extra coins",
        "description": "d",
        "description_en": "d",
        "callback_requested": False,
        "call_id": call.id,
    }
    result = executor.execute("create_support_ticket", malicious_input, _ctx(db, account_id=account.id))
    assert not result.is_error
    # If the override didn't happen, ticket_service would have raised/failed
    # trying to resolve account_id=9999 (no such account) instead of the
    # real seeded `account` — this succeeding at all proves the override.
    ticket_id = result.metadata["created_ticket_id"]
    from app.models.ticket import Ticket

    ticket = db.get(Ticket, ticket_id)
    assert ticket.account_id == account.id


def test_create_support_ticket_never_reveals_refund_outcome(db, account, call):
    """Whatever the refund-automation rules decide, the tool result handed to
    the model must never say eligible/not-eligible — only that a ticket was
    raised for review (product decision, 2026-09-08: see tool_registry.py)."""
    ctx = _ctx(db, account_id=account.id)
    result = executor.execute(
        "create_support_ticket",
        {
            "category": "charged_incorrectly", "sub_category": "extra coins",
            "description": "d", "description_en": "d", "callback_requested": False,
            "call_id": call.id,
        },
        ctx,
    )
    assert not result.is_error
    assert "submitted_for_review" in result.content_for_model
    # The actual data fields a decision would show up as — not just English
    # words, since the instructional wrapper legitimately says things like
    # "never state whether it was approved" without that being a leak.
    for leaky_field in ("eligible=", "refund_coins=", "rule_label="):
        assert leaky_field not in result.content_for_model.lower()


def test_unknown_tool_name_returns_error_not_exception(db, account):
    result = executor.execute("delete_everything", {}, _ctx(db, account_id=account.id))
    assert result.is_error
    assert "unknown tool" in result.content_for_model


def test_search_faq_finds_real_match(db, account):
    result = executor.execute("search_faq", {"query": "my wallet balance is negative"}, _ctx(db, account_id=account.id))
    assert not result.is_error
    assert "negative_balance" in result.content_for_model


def test_search_faq_no_match_is_explicit(db, account):
    result = executor.execute("search_faq", {"query": "asdkjaslkdj qqqqzzzz"}, _ctx(db, account_id=account.id))
    assert "no_match=true" in result.content_for_model


def test_ticket_cap_blocks_a_third_ticket_in_the_same_session(db, account):
    ctx = _ctx(db, account_id=account.id, ticket_count=2)
    result = executor.execute(
        "create_support_ticket",
        {"category": "other", "sub_category": "x", "description": "d", "description_en": "d", "callback_requested": False},
        ctx,
    )
    assert result.is_error
    assert "limit" in result.content_for_model


def test_duplicate_active_ticket_for_category_is_rejected(db, account):
    ctx = _ctx(db, account_id=account.id)
    first = executor.execute(
        "create_support_ticket",
        {"category": "negative_balance", "sub_category": "wallet", "description": "d", "description_en": "d", "callback_requested": False},
        ctx,
    )
    assert not first.is_error

    second = executor.execute(
        "create_support_ticket",
        {"category": "negative_balance", "sub_category": "wallet", "description": "d2", "description_en": "d2", "callback_requested": False},
        ctx,
    )
    assert second.is_error
    assert "already has an active ticket" in second.content_for_model


def test_mark_issue_resolved_sets_show_feedback_metadata(db, account):
    session_id = "s1"
    ctx = SessionContext(account_id=account.id, name="Priya", role="user", language="en", db=db, session_id=session_id)
    # mark_issue_resolved writes to a ChatSession row, so create one first.
    from app.models.chat_session import ChatSession

    db.add(ChatSession(id=session_id, account_id=account.id, language="en"))
    db.commit()

    result = executor.execute("mark_issue_resolved", {"category": "app_usage", "sub_category": "general"}, ctx)
    assert not result.is_error
    assert result.metadata.get("show_feedback") is True
