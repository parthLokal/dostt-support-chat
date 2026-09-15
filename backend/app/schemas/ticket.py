from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import TicketStatus


class TicketStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: TicketStatus
    note: str | None
    changed_by: str
    changed_at: datetime


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    category: str
    sub_category: str
    description: str
    description_en: str
    status: TicketStatus
    escalation_team: str | None
    callback_requested: bool
    refund_checked: bool
    refund_rule_label: str | None
    real_ticket_id: int | None
    attachment_path: str | None
    assigned_admin_id: int | None
    sla_due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    history: list[TicketStatusHistoryRead] = []


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    note: str | None = None


class TicketIntakeRequest(BaseModel):
    """A ticket entering the system directly — from anywhere other than the
    Gemini chat turn (e.g. the in-app Help & Support form, or a CS agent
    logging a call-in complaint). See ticket_service.create_ticket_with_automation:
    for the three refund-driven categories, if `call_id` is given the v1.1
    refund-automation rules run immediately, synchronously, right here —
    triggered by this row entering the table, not by anything Gemini decided.
    """

    user_id: str
    category: str
    sub_category: str = "general"
    description: str
    description_en: str | None = None
    call_id: int | None = None
    callback_requested: bool = False
    # For the real Dostt ticket-creation API mirror — see ticket_service.py's
    # _mirror_to_real_api and app/data/issue_catalog.py. All optional; absent
    # means the mirror is skipped and only the local ticket is created.
    auth_token: str | None = None
    language_id: int | None = None
    user_type_code: int | None = None
    country_code: str | None = None
