from app.core.config import settings
from app.services import ticket_service


def _login(client, email):
    resp = client.post("/api/admin/login", json={"email": email, "password": settings.ADMIN_PASSWORD})
    assert resp.status_code == 200
    return resp.json()["token"]


def test_login_wrong_password_is_unauthorized(client, admin):
    resp = client.post("/api/admin/login", json={"email": admin.email, "password": "wrong"})
    assert resp.status_code == 401


def test_login_succeeds_for_seeded_admin(client, admin):
    token = _login(client, admin.email)
    assert token


def test_queue_requires_auth(client):
    resp = client.get("/api/admin/tickets")
    assert resp.status_code == 401


def test_queue_lists_tickets_after_login(client, db, account, admin):
    ticket_service.create_ticket(
        db, account_id=account.id, category="negative_balance", sub_category="x",
        description="d", description_en="d", preferred_language="en",
    )
    token = _login(client, admin.email)
    resp = client.get("/api/admin/tickets", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_admin_cannot_set_status_to_submitted_directly(client, db, account, admin):
    ticket = ticket_service.create_ticket(
        db, account_id=account.id, category="other", sub_category="x",
        description="d", description_en="d", preferred_language="en",
    )
    token = _login(client, admin.email)
    resp = client.patch(
        f"/api/admin/tickets/{ticket.id}/status",
        json={"status": "submitted"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_admin_can_move_ticket_to_resolved(client, db, account, admin):
    ticket = ticket_service.create_ticket(
        db, account_id=account.id, category="other", sub_category="x",
        description="d", description_en="d", preferred_language="en",
    )
    token = _login(client, admin.email)
    resp = client.patch(
        f"/api/admin/tickets/{ticket.id}/status",
        json={"status": "resolved", "note": "fixed it"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
