# MOCKED under MOCK_MODE — otherwise backed by real production data via the
# "Recent calls" Redash query (id in settings.REDASH_QUERY_RECENT_CALLS),
# confirmed against real rows on 2026-09-08 (see app/integrations/redash_client.py).
# That saved query already does the service-code -> 'audio'/'video' mapping
# and filters out never-connected bookings (started_at IS NULL) — this file
# just shapes the rows into our own Call model.
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations import redash_client
from app.integrations.config import MOCK_MODE
from app.models.account import Account
from app.models.call import Call

logger = logging.getLogger(__name__)


def _calls_from_redash(account_id: int, user_id: str, limit: int) -> list[Call]:
    rows = redash_client.run_query(
        settings.REDASH_QUERY_RECENT_CALLS, {"user_id": user_id}, max_age=300
    )
    calls = []
    for row in rows[:limit]:
        if row.get("duration_sec") is None or row.get("coins_debited") is None:
            continue  # belt-and-suspenders; the saved query already excludes these
        calls.append(
            Call(
                id=row["id"],
                account_id=account_id,
                call_type=row.get("call_type") or "audio",
                duration_sec=int(row["duration_sec"]),
                coins_debited=int(round(float(row["coins_debited"]))),
                # The real counterpart's name isn't in this query's columns yet
                # (it only has expert_id/customer_id) — a real name needs a
                # separate lookup that hasn't been wired up. Placeholder only.
                counterpart_name="Dostt Listener",
                has_open_ticket=False,
            )
        )
    return calls


def get_recent_calls(db: Session, account_id: int, limit: int = 5) -> list[Call]:
    rows = (
        db.execute(
            select(Call)
            .where(Call.account_id == account_id, Call.has_open_ticket.is_(False))
            .order_by(Call.occurred_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    if rows:
        return list(rows)

    if not MOCK_MODE:
        account = db.get(Account, account_id)
        if account is None:
            return []
        try:
            return _calls_from_redash(account_id, account.user_id, limit)
        except Exception:
            logger.exception("Redash recent-calls lookup failed for account %s", account_id)
            return []

    # No seeded call history for this account — fabricate one deterministic
    # call so the guided Calls flow always has something to show in a demo.
    # Never persisted, so it won't collide with `has_open_ticket` bookkeeping.
    account = db.get(Account, account_id)
    seed = account_id % 2
    return [
        Call(
            id=-account_id,
            account_id=account_id,
            call_type="audio" if seed == 0 else "video",
            duration_sec=35 + (account_id * 7) % 40,
            coins_debited=20 + (account_id * 3) % 60,
            counterpart_name="Dostt Listener" if account and account.role.value == "user" else f"User {90000 + account_id}",
            has_open_ticket=False,
        )
    ]


def get_call(db: Session, account_id: int, call_id: int) -> Call | None:
    # Real Redash-sourced call ids are ordinary positive booking ids — never
    # rows in our own `calls` table — so a local-table miss doesn't mean the
    # call doesn't exist, only that it isn't persisted locally. Fall back to
    # matching against get_recent_calls() either way (covers both that case
    # and the MOCK_MODE negative-placeholder-id case).
    if call_id >= 0:
        call = db.get(Call, call_id)
        if call is not None and call.account_id == account_id:
            return call
    calls = get_recent_calls(db, account_id)
    return next((c for c in calls if c.id == call_id), None)
