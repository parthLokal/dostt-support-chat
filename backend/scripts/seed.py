"""Seeds demo accounts (the same six personas the original prototype used —
a first-timer, a repeat-abuse pattern, two genuine-history accounts, a VIP,
and a Listener), a few calls/transactions each, and one admin. Run with:

    python -m scripts.seed
"""

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.account import Account
from app.models.admin import Admin
from app.models.call import Call
from app.models.enums import AccountRole
from app.models.transaction import Transaction

ACCOUNTS = [
    dict(
        user_id="90001", name="Priya", role=AccountRole.USER,
        ltv_value_inr=450, tickets_raised=0, refunded_tickets=0, ltv_coins=450, refund_coins_lifetime=0,
        calls=[("audio", 38, 40, "Ananya"), ("video", 210, 210, "Rhea")],
        transactions=[("recharge", 99, 100, "success")],
    ),
    dict(
        user_id="90002", name="Vikram", role=AccountRole.USER,
        ltv_value_inr=80, tickets_raised=46, refunded_tickets=30, ltv_coins=360, refund_coins_lifetime=260,
        calls=[("audio", 18, 20, "Meera"), ("audio", 94, 40, "Kavya")],
        transactions=[("recharge", 49, 40, "success")],
    ),
    dict(
        user_id="90003", name="Arjun", role=AccountRole.USER,
        ltv_value_inr=2400, tickets_raised=13, refunded_tickets=11, ltv_coins=7830, refund_coins_lifetime=900,
        calls=[("video", 45, 60, "Isha"), ("audio", 65, 30, "Sara")],
        transactions=[("recharge", 199, 200, "pending"), ("recharge", 199, 200, "success")],
    ),
    dict(
        user_id="90004", name="Karthik", role=AccountRole.USER,
        ltv_value_inr=8681, tickets_raised=10, refunded_tickets=9, ltv_coins=37010, refund_coins_lifetime=900,
        calls=[("video", 10, 60, "Nisha"), ("audio", 55, 20, "Divya")],
        transactions=[("recharge", 999, 1000, "success")],
    ),
    dict(
        user_id="90005", name="Rohan", role=AccountRole.USER,
        ltv_value_inr=21500, tickets_raised=4, refunded_tickets=3, ltv_coins=92000, refund_coins_lifetime=600,
        calls=[("audio", 200, 130, "Tanya"), ("video", 120, 140, "Neha")],
        transactions=[("recharge", 4999, 5000, "success")],
    ),
    dict(
        user_id="90006", name="Ananya", role=AccountRole.LISTENER,
        ltv_value_inr=3000, tickets_raised=6, refunded_tickets=5, ltv_coins=12000, refund_coins_lifetime=300,
        calls=[("audio", 300, 0, "User 88213"), ("video", 480, 0, "User 44921")],
        transactions=[("withdrawal", 850, 0, "processing"), ("withdrawal", 1200, 0, "success")],
    ),
]


def run() -> None:
    db = SessionLocal()
    try:
        for spec in ACCOUNTS:
            existing = db.query(Account).filter_by(user_id=spec["user_id"]).one_or_none()
            if existing:
                print(f"Skipping {spec['name']} — user_id {spec['user_id']} already seeded")
                continue
            account = Account(
                user_id=spec["user_id"],
                name=spec["name"],
                role=spec["role"],
                ltv_value_inr=spec["ltv_value_inr"],
                tickets_raised=spec["tickets_raised"],
                refunded_tickets=spec["refunded_tickets"],
                ltv_coins=spec["ltv_coins"],
                refund_coins_lifetime=spec["refund_coins_lifetime"],
            )
            db.add(account)
            db.flush()

            for call_type, duration_sec, coins, counterpart in spec["calls"]:
                db.add(Call(account_id=account.id, call_type=call_type, duration_sec=duration_sec, coins_debited=coins, counterpart_name=counterpart))

            for kind, amount, coins, status in spec["transactions"]:
                db.add(Transaction(account_id=account.id, kind=kind, amount_inr=amount, coins=coins, status=status))

            print(f"Seeded {spec['role'].value} '{spec['name']}' — user_id={spec['user_id']} (account_id={account.id})")

        if not db.query(Admin).filter_by(email=settings.OWNER_EMAIL).one_or_none():
            db.add(Admin(name="Owner", email=settings.OWNER_EMAIL))
            print(f"Seeded owner admin '{settings.OWNER_EMAIL}'")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
