from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base
from app.models.enums import TicketStatus

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class TicketStatusHistory(Base):
    """Append-only log of every status change. `Ticket.status` always mirrors
    the latest row here — enforced entirely in app/services/ticket_service.py
    (the only module allowed to write either), not a DB trigger.
    """

    __tablename__ = "ticket_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus, name="ticket_status", native_enum=False))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str] = mapped_column(String(120), default="system")
    changed_at: Mapped[datetime] = mapped_column(default=utcnow)

    ticket: Mapped["Ticket"] = relationship(back_populates="history")
