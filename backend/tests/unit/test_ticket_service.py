from app.models.enums import TicketStatus
from app.services import ticket_service


def _create(db, account, category="other", sub_category="x"):
    return ticket_service.create_ticket(
        db, account_id=account.id, category=category, sub_category=sub_category,
        description="d", description_en="d", preferred_language="en",
    )


def test_create_ticket_starts_submitted_then_auto_assigns(db, account, admin):
    ticket = _create(db, account)
    assert ticket.status == TicketStatus.ASSIGNED
    assert ticket.assigned_admin_id == admin.id
    statuses = [h.status for h in ticket.history]
    assert statuses == [TicketStatus.SUBMITTED, TicketStatus.ASSIGNED]


def test_status_always_mirrors_latest_history_row(db, account, admin):
    ticket = _create(db, account)
    ticket_service.update_status(db, ticket, TicketStatus.IN_PROGRESS, note="looking into it", changed_by="Test Admin")
    assert ticket.status == TicketStatus.IN_PROGRESS
    assert ticket.history[-1].status == TicketStatus.IN_PROGRESS
    assert ticket.history[-1].note == "looking into it"


def test_no_active_ticket_found_for_a_fresh_category(db, account):
    assert ticket_service.get_active_ticket_for_category(db, account.id, "negative_balance") is None


def test_active_ticket_found_until_resolved(db, account, admin):
    ticket = _create(db, account, category="negative_balance")
    assert ticket_service.get_active_ticket_for_category(db, account.id, "negative_balance") is not None

    ticket_service.update_status(db, ticket, TicketStatus.RESOLVED, note=None, changed_by="Test Admin")
    assert ticket_service.get_active_ticket_for_category(db, account.id, "negative_balance") is None


def test_escalation_team_assigned_from_category(db, account, admin):
    ticket = _create(db, account, category="report_user")
    assert ticket.escalation_team == "Trust & Safety"


def test_list_tickets_for_account_orders_newest_first(db, account, admin):
    first = _create(db, account, category="app_usage")
    second = _create(db, account, category="negative_balance")
    tickets = ticket_service.list_tickets_for_account(db, account.id)
    assert [t.id for t in tickets] == [second.id, first.id]
