"""Proves the real (non-MOCK_MODE) path in call_client.py: shapes Redash rows
into Call objects, skips null-duration rows defensively, degrades to an
empty list on a Redash failure rather than raising, and get_call() can find
a real positive Redash-sourced id (never persisted locally) via
get_recent_calls() rather than only a local-table lookup.
"""

from app.integrations import call_client


def test_get_recent_calls_shapes_redash_rows(db, account, monkeypatch):
    monkeypatch.setattr(call_client, "MOCK_MODE", False)
    monkeypatch.setattr(
        call_client.redash_client,
        "run_query",
        lambda *a, **kw: [
            {"id": 402103759, "call_type": "audio", "duration_sec": 27, "coins_debited": 10.0,
             "customer_id": 16858575, "expert_id": 17400005, "started_at": "2026-08-14 08:46"},
            {"id": 401195579, "call_type": "audio", "duration_sec": None, "coins_debited": None,
             "customer_id": 16858575, "expert_id": 1428172, "started_at": None},
        ],
    )

    calls = call_client.get_recent_calls(db, account.id)

    assert len(calls) == 1  # the null-duration row is skipped
    assert calls[0].id == 402103759
    assert calls[0].call_type == "audio"
    assert calls[0].duration_sec == 27
    assert calls[0].coins_debited == 10


def test_get_recent_calls_degrades_to_empty_on_redash_failure(db, account, monkeypatch):
    monkeypatch.setattr(call_client, "MOCK_MODE", False)

    def boom(*a, **kw):
        raise RuntimeError("redash down")

    monkeypatch.setattr(call_client.redash_client, "run_query", boom)

    assert call_client.get_recent_calls(db, account.id) == []


def test_get_call_finds_real_id_via_recent_calls(db, account, monkeypatch):
    monkeypatch.setattr(call_client, "MOCK_MODE", False)
    monkeypatch.setattr(
        call_client.redash_client,
        "run_query",
        lambda *a, **kw: [
            {"id": 402103759, "call_type": "audio", "duration_sec": 27, "coins_debited": 10.0,
             "customer_id": 16858575, "expert_id": 17400005, "started_at": "2026-08-14 08:46"},
        ],
    )

    found = call_client.get_call(db, account.id, 402103759)
    assert found is not None
    assert found.duration_sec == 27

    assert call_client.get_call(db, account.id, 999999999) is None
