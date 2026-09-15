from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account


class Transaction(Base):
    """A recharge, withdrawal, or earnings-payout record — stands in for the
    real Metabase-sourced data the SOP checks ("Payment order with mobile
    number" / "Expert Payouts"). Seeded per account by scripts/seed.py.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)

    kind: Mapped[str] = mapped_column(String(20))  # "recharge" | "withdrawal"
    amount_inr: Mapped[int] = mapped_column(Integer)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20))  # "pending" | "success" | "failed" | "processing"
    occurred_at: Mapped[datetime] = mapped_column(default=utcnow)

    account: Mapped["Account"] = relationship(back_populates="transactions")
