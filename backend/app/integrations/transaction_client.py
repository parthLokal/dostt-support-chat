# MOCKED under MOCK_MODE for both kinds. Recharges are otherwise backed by
# real production data via the "Recent recharges" Redash query (id in
# settings.REDASH_QUERY_RECENT_RECHARGES), confirmed against real rows on
# 2026-09-08 — that saved query already filters to type=1 (real recharges,
# excludes free/bonus coin grants). Withdrawals are backed by the "Recent
# withdrawals" query (id in settings.REDASH_QUERY_RECENT_WITHDRAWALS) —
# public_payouts_expertpayout confirmed as the live payout table on
# 2026-09-09 (it had a same-day row vs. public_payments_dosttexpertpayout's
# stale 2025-09-25 one). Unlike recharge status codes, withdrawal status
# codes have NOT been empirically confirmed against a real row yet (only
# sourced from the SOP doc: Processing/Successful/Reversed/Failed) — see
# _withdrawal_status_label.
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations import redash_client
from app.integrations.config import MOCK_MODE
from app.models.account import Account
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# Confirmed empirically against real production data (2026-09-08): 0=Pending/
# Processing, 1=Paid, 4=Failed. No other codes observed — an unrecognized
# code is surfaced as its raw string rather than guessed at.
_RECHARGE_STATUS_BY_CODE = {0: "pending", 1: "success", 4: "failed"}

_WITHDRAWAL_STATUSES = ["success", "processing", "reversed", "failed"]


def _withdrawal_status_label(raw_status: object) -> str:
    # No confirmed code->label mapping exists yet (unlike recharges) — always
    # surface the raw value rather than guess. Fix this the same way we
    # fixed recharges: test against a real withdrawal of known status first.
    return str(raw_status)


def _recharges_from_redash(user_id: str, limit: int) -> list[Transaction]:
    rows = redash_client.run_query(
        settings.REDASH_QUERY_RECENT_RECHARGES, {"user_id": user_id}, max_age=300
    )
    out = []
    for row in rows[:limit]:
        status = _RECHARGE_STATUS_BY_CODE.get(row.get("status"), str(row.get("status")))
        out.append(
            Transaction(
                id=row["id"],
                kind="recharge",
                amount_inr=round(float(row.get("amount_inr") or 0)),
                coins=int(row.get("coins") or 0),
                status=status,
            )
        )
    return out


def _withdrawals_from_redash(user_id: str, limit: int) -> list[Transaction]:
    rows = redash_client.run_query(
        settings.REDASH_QUERY_RECENT_WITHDRAWALS, {"user_id": user_id}, max_age=300
    )
    out = []
    for row in rows[:limit]:
        out.append(
            Transaction(
                id=row["id"],
                kind="withdrawal",
                amount_inr=round(float(row.get("amount") or 0)),
                coins=0,
                status=_withdrawal_status_label(row.get("status")),
            )
        )
    return out


def get_recent_transactions(db: Session, account_id: int, kind: str, limit: int = 5) -> list[Transaction]:
    rows = (
        db.execute(
            select(Transaction)
            .where(Transaction.account_id == account_id, Transaction.kind == kind)
            .order_by(Transaction.occurred_at.desc())
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
            if kind == "recharge":
                return _recharges_from_redash(account.user_id, limit)
            return _withdrawals_from_redash(account.user_id, limit)
        except Exception:
            logger.exception("Redash recent-%ss lookup failed for account %s", kind, account_id)
            return []

    if kind == "recharge":
        seed = account_id % len(_RECHARGE_STATUS_BY_CODE)
        statuses = list(_RECHARGE_STATUS_BY_CODE.values())
        return [
            Transaction(
                id=-account_id,
                account_id=account_id,
                kind="recharge",
                amount_inr=99 + (account_id * 11) % 400,
                coins=100 + (account_id * 11) % 400,
                status=statuses[seed],
            )
        ]
    seed = account_id % len(_WITHDRAWAL_STATUSES)
    return [
        Transaction(
            id=-account_id,
            account_id=account_id,
            kind="withdrawal",
            amount_inr=500 + (account_id * 53) % 2000,
            coins=0,
            status=_WITHDRAWAL_STATUSES[seed],
        )
    ]


def get_transaction(db: Session, account_id: int, transaction_id: int, kind: str) -> Transaction | None:
    if transaction_id < 0:
        txs = get_recent_transactions(db, account_id, kind)
        return next((t for t in txs if t.id == transaction_id), None)
    tx = db.get(Transaction, transaction_id)
    if tx is None or tx.account_id != account_id:
        return None
    return tx
