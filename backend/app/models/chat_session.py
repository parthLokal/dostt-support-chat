from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base
from app.models.enums import SessionResolution

if TYPE_CHECKING:
    from app.models.chat_message import ChatMessage


class ChatSession(Base):
    """One chat-webview visit. Powers the PRD's session-level analytics
    (fallback rate, escalation rate, category distribution) — see
    app/services/chat_session_service.py.
    """

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    language: Mapped[str] = mapped_column(String(8), default="en")

    resolution: Mapped[SessionResolution | None] = mapped_column(
        Enum(SessionResolution, name="session_resolution", native_enum=False), nullable=True
    )
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sub_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ticket_count: Mapped[int] = mapped_column(default=0)

    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", order_by="ChatMessage.created_at", cascade="all, delete-orphan"
    )
