from app.services import ticket_service


def test_create_ticket_via_intake_route(client, account, admin):
    resp = client.post(
        "/api/tickets",
        json={
            "user_id": account.user_id,
            "category": "negative_balance",
            "sub_category": "wallet",
            "description": "My wallet shows negative",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "negative_balance"
    assert body["status"] == "assigned"


def test_create_ticket_via_intake_route_runs_refund_automation(client, db, account, admin):
    account.ltv_value_inr = 8681
    account.tickets_raised = 10
    account.refunded_tickets = 9
    db.commit()
    from app.models.call import Call

    call = Call(account_id=account.id, call_type="audio", duration_sec=20, coins_debited=10, counterpart_name="Meera")
    db.add(call)
    db.commit()
    db.refresh(call)

    resp = client.post(
        "/api/tickets",
        json={
            "user_id": account.user_id,
            "category": "charged_incorrectly",
            "sub_category": "extra coins",
            "description": "extra coins deducted",
            "call_id": call.id,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "resolved"
    assert body["refund_checked"] is True


def test_create_ticket_via_intake_route_rejects_duplicate(client, account, admin):
    payload = {"user_id": account.user_id, "category": "negative_balance", "sub_category": "wallet", "description": "d"}
    first = client.post("/api/tickets", json=payload)
    assert first.status_code == 200
    second = client.post("/api/tickets", json=payload)
    assert second.status_code == 409


def test_create_ticket_via_intake_route_unknown_user(client):
    resp = client.post(
        "/api/tickets",
        json={"user_id": "does-not-exist", "category": "other", "sub_category": "x", "description": "d"},
    )
    assert resp.status_code == 404


def test_list_my_tickets_empty(client, account):
    resp = client.get(f"/api/tickets?account_id={account.id}")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_my_tickets_after_creating_one(client, db, account, admin):
    ticket_service.create_ticket(
        db, account_id=account.id, category="other", sub_category="x",
        description="d", description_en="d", preferred_language="en",
    )
    resp = client.get(f"/api/tickets?account_id={account.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["category"] == "other"
