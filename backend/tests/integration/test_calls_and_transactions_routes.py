def test_list_recent_calls(client, account, call):
    resp = client.get(f"/api/calls?account_id={account.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == call.id
    assert body[0]["call_type"] == "audio"


def test_list_recent_calls_falls_back_to_mocked_data_when_none_seeded(client, account):
    resp = client.get(f"/api/calls?account_id={account.id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1  # deterministic mocked fallback, not empty


def test_list_recent_transactions(client, account):
    resp = client.get(f"/api/transactions?account_id={account.id}&kind=recharge")
    assert resp.status_code == 200
    assert resp.json()[0]["kind"] == "recharge"


def test_transactions_rejects_bad_kind(client, account):
    resp = client.get(f"/api/transactions?account_id={account.id}&kind=bogus")
    assert resp.status_code == 422
