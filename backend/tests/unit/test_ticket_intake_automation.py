"""Proves the "automations triggered off backend tables, not chat" mechanism:
create_ticket_with_automation resolves refund-driven tickets synchronously,
using only account/call rows already in the database — no agent, no Gemini.
"""

from app.models.call import Call
from app.models.enums import TicketStatus
from app.services import ticket_service


def test_eligible_refund_auto_resolves_ticket_on_creation(db, account, admin):
    account.ltv_value_inr = 8681
    account.tickets_raised = 10
    account.refunded_tickets = 9  # 90% genuine history -> High LTV eligible
    call = Call(account_id=account.id, call_type="audio", duration_sec=30, coins_debited=10, counterpart_name="Meera")
    db.add(call)
    db.commit()
    db.refresh(call)

    ticket = ticket_service.create_ticket_with_automation(
        db, account_id=account.id, category="charged_incorrectly", sub_category="extra coins",
        description="d", description_en="d", call_id=call.id,
    )
    assert ticket.status == TicketStatus.RESOLVED
    assert ticket.refund_checked is True
    assert "genuine history" in ticket.refund_rule_label
    assert "Auto-refunded" in ticket.history[-1].note


def test_not_eligible_refund_leaves_ticket_assigned_for_review(db, account, admin):
    account.ltv_value_inr = 80
    account.tickets_raised = 46
    account.refunded_tickets = 30  # ~65% -- below the 70% bar, blocked
    call = Call(account_id=account.id, call_type="audio", duration_sec=18, coins_debited=20, counterpart_name="Meera")
    db.add(call)
    db.commit()
    db.refresh(call)

    ticket = ticket_service.create_ticket_with_automation(
        db, account_id=account.id, category="charged_incorrectly", sub_category="extra coins",
        description="d", description_en="d", call_id=call.id,
    )
    assert ticket.status == TicketStatus.ASSIGNED
    assert ticket.refund_checked is True
    assert "below 70%" in ticket.refund_rule_label


def test_non_refund_category_creates_ticket_without_automation(db, account, admin):
    ticket = ticket_service.create_ticket_with_automation(
        db, account_id=account.id, category="negative_balance", sub_category="wallet",
        description="d", description_en="d",
    )
    assert ticket.refund_checked is False
    assert ticket.refund_rule_label is None
    assert ticket.status == TicketStatus.ASSIGNED


def test_refund_driven_category_without_call_id_skips_automation(db, account, admin):
    ticket = ticket_service.create_ticket_with_automation(
        db, account_id=account.id, category="charged_incorrectly", sub_category="extra coins",
        description="d", description_en="d", call_id=None,
    )
    assert ticket.refund_checked is False
    assert ticket.status == TicketStatus.ASSIGNED
