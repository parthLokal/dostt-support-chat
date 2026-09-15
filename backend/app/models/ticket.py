from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base
from app.models.enums import TicketStatus

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.admin import Admin
    from app.models.ticket_status_history import TicketStatusHistory


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)

    category: Mapped[str] = mapped_column(String(80))
    sub_category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    description_en: Mapped[str] = mapped_column(Text)
    preferred_language: Mapped[str] = mapped_column(String(8))

    # Filled in only for refund-driven categories (charged_incorrectly,
    # cannot_hear, not_showing_face) that were routed to a ticket because the
    # automation engine did NOT approve an automatic refund — see
    # app/services/refund_service.py. Lets an admin see at a glance why this
    # landed on their queue instead of resolving itself.
    refund_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    refund_rule_label: Mapped[str | None] = mapped_column(String(120), nullable=True)

    callback_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_team: Mapped[str | None] = mapped_column(String(120), nullable=True)
    assigned_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id"), nullable=True)

    # Set at creation from the "Dostt_Refund SOP" doc's User-Based SLA table
    # (see app/services/refund_service.sla_hours_for) — a due-by time, not a
    # remaining-duration counter, so it stays meaningful even if nobody reads
    # it until well after creation.
    sla_due_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Set only when app/integrations/dostt_api_client.create_ticket() actually
    # succeeded — the id the real Dostt backend assigned this ticket. Null
    # whenever we couldn't attempt the real call (missing auth_token/
    # language_id, an unmapped category — see app/data/issue_catalog.py — or
    # the call itself failed); this row is still the ticket of record either
    # way, just not yet mirrored to the real system in that case.
    real_ticket_id: Mapped[int | None] = mapped_column(nullable=True)

    # Set when the account attached a screenshot in chat before this ticket
    # was raised (see app/services/attachment_service.py) — the same file
    # forwarded to the real API's `files` part. Null means no attachment.
    attachment_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", native_enum=False),
        default=TicketStatus.SUBMITTED,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    account: Mapped["Account"] = relationship()
    assigned_admin: Mapped["Admin | None"] = relationship()
    history: Mapped[list["TicketStatusHistory"]] = relationship(
        back_populates="ticket",
        order_by="TicketStatusHistory.changed_at",
        cascade="all, delete-orphan",
    )
