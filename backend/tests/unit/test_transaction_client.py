"""Proves the real (non-MOCK_MODE) path in transaction_client.py: recharges
are shaped from Redash rows with the confirmed status-code mapping,
withdrawals are shaped too (payout table confirmed 2026-09-09) but surface
their raw, unconfirmed status code rather than a guessed label, and a Redash
failure degrades to an empty list rather than raising.
"""

from app.integrations import transaction_client


def test_get_recent_recharges_maps_confirmed_status_codes(db, account, monkeypatch):
    monkeypatch.setattr(transaction_client, "MOCK_MODE", False)
    monkeypatch.setattr(
        transaction_client.redash_client,
        "run_query",
        lambda *a, **kw: [
            {"id": 50073871, "amount_inr": 16.95, "coins": 130, "status": 1, "occurred_at": "2026-07-14 06:02"},
            {"id": 49841922, "amount_inr": 16.95, "coins": 130, "status": 4, "occurred_at": "2026-07-12 19:39"},
            {"id": 49422286, "amount_inr": 16.95, "coins": 130, "status": 0, "occurred_at": "2026-07-10 13:23"},
        ],
    )

    txs = transaction_client.get_recent_transactions(db, account.id, "recharge")

    assert [t.status for t in txs] == ["success", "failed", "pending"]
    assert txs[0].amount_inr == 17  # rounded from 16.95
    assert txs[0].coins == 130


def test_get_recent_withdrawals_shapes_rows_with_raw_status(db, account, monkeypatch):
    monkeypatch.setattr(transaction_client, "MOCK_MODE", False)
    monkeypatch.setattr(
        transaction_client.redash_client,
        "run_query",
        lambda *a, **kw: [
            {"id": 12345, "amount": 999.5, "status": 2, "created_on": "2026-09-09 14:35"},
        ],
    )

    txs = transaction_client.get_recent_transactions(db, account.id, "withdrawal")

    assert len(txs) == 1
    assert txs[0].kind == "withdrawal"
    assert txs[0].amount_inr == 1000  # rounded from 999.5
    # Not mapped to a label like recharges — status codes here are unconfirmed.
    assert txs[0].status == "2"


def test_get_recent_recharges_degrades_to_empty_on_redash_failure(db, account, monkeypatch):
    monkeypatch.setattr(transaction_client, "MOCK_MODE", False)

    def boom(*a, **kw):
        raise RuntimeError("redash down")

    monkeypatch.setattr(transaction_client.redash_client, "run_query", boom)

    assert transaction_client.get_recent_transactions(db, account.id, "recharge") == []


def test_get_recent_withdrawals_degrades_to_empty_on_redash_failure(db, account, monkeypatch):
    monkeypatch.setattr(transaction_client, "MOCK_MODE", False)

    def boom(*a, **kw):
        raise RuntimeError("redash down")

    monkeypatch.setattr(transaction_client.redash_client, "run_query", boom)

    assert transaction_client.get_recent_transactions(db, account.id, "withdrawal") == []
