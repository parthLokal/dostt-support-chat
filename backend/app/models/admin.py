from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class Admin(Base):
    """A CS Lead / L1-L2 agent with dashboard access. Single access tier —
    Dostt's SOP doesn't have AstroHelp's KAM-vs-CS routing split, just L1/L2
    and named escalation teams (Trust & Safety, Tech Support, Refund) — see
    app/services/ticket_service.py's ESCALATION_TEAM_BY_CATEGORY.
    """

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
