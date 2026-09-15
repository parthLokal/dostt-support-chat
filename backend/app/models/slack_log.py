from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class SlackLog(Base):
    """Every mocked Slack notification, real or not — what the admin
    dashboard's Slack Log page reads. See app/integrations/slack_client.py.
    """

    __tablename__ = "slack_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(Text)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
