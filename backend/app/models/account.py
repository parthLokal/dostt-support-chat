from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base
from app.models.enums import AccountRole

if TYPE_CHECKING:
    from app.models.call import Call
    from app.models.transaction import Transaction


class Account(Base):
    """A Dostt user or Listener (Super Dostt). Stands in for the main app's
    own user table — the chatbot backend never owns identity, it only
    resolves the `user_id` the host app hands off (see api/routes/session.py)
    against this table, the same handoff shape the AstroHelp sibling project
    uses for astrologers.

    ltv_value_inr / tickets_raised / refunded_tickets / ltv_coins /
    refund_coins_lifetime are exactly the inputs the v1.1 refund-automation
    PRD's rules run on (see app/services/refund_service.py) — in a real
    deployment these would be read live from the billing/ticketing systems
    instead of stored here; they're columns only so scripts/seed.py can give
    each demo account a stable, plausible history.
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[AccountRole] = mapped_column(Enum(AccountRole, name="account_role", native_enum=False))
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")

    # The real customers_customer.onboarded_language_id — looked up once via
    # Redash at account-creation time for a real user (see
    # api/routes/session.py's _resolve_role_and_language, confirmed against
    # real data 2026-09-10), used as the ticket-mirror's language_id when the
    # frontend hasn't sent one itself. Null for Listener-only accounts (no
    # customers_customer row) and for local seed/demo accounts.
    onboarded_language_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    ltv_value_inr: Mapped[float] = mapped_column(Float, default=0)
    tickets_raised: Mapped[int] = mapped_column(Integer, default=0)
    refunded_tickets: Mapped[int] = mapped_column(Integer, default=0)
    ltv_coins: Mapped[int] = mapped_column(Integer, default=0)
    refund_coins_lifetime: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    calls: Mapped[list["Call"]] = relationship(back_populates="account", order_by="Call.occurred_at.desc()")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="account", order_by="Transaction.occurred_at.desc()"
    )
