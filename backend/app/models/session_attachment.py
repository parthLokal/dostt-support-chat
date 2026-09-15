from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class SessionAttachment(Base):
    """An image uploaded mid-chat, pending attachment to whichever ticket
    gets raised next in this session. DB-backed (not an in-process dict) so
    it survives across multiple worker processes — the same reason chat
    history itself is re-sent by the frontend rather than cached in memory.

    One pending row per session at a time: uploading a new image replaces
    the previous one (see attachment_service.py); a row is deleted once
    consumed by create_support_ticket, so leftover rows only mean "this
    session uploaded something that was never used to raise a ticket."
    """

    __tablename__ = "session_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), index=True, unique=True)

    file_path: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    original_filename: Mapped[str] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
