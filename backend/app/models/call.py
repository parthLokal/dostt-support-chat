from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account


class Call(Base):
    """A recent audio/video session, standing in for the real Stream/Django
    booking record the actual SOP checks refund-eligibility against (see
    Refund SOP: "Check the call type, Accumulated Users details and Call
    duration timeline in stream"). Seeded per account by scripts/seed.py.
    """

    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)

    call_type: Mapped[str] = mapped_column(String(10))  # "audio" | "video"
    duration_sec: Mapped[int] = mapped_column(Integer)
    coins_debited: Mapped[int] = mapped_column(Integer)
    counterpart_name: Mapped[str] = mapped_column(String(120))
    occurred_at: Mapped[datetime] = mapped_column(default=utcnow)
    has_open_ticket: Mapped[bool] = mapped_column(default=False)

    account: Mapped["Account"] = relationship(back_populates="calls")
