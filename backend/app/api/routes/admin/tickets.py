from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.errors import AppError, NotFoundError
from app.db.session import get_db
from app.models.admin import Admin
from app.models.enums import ADMIN_SETTABLE_STATUSES, TicketStatus
from app.models.ticket import Ticket
from app.schemas.ticket import TicketRead, TicketStatusUpdate
from app.services import ticket_service

router = APIRouter(prefix="/api/admin/tickets", tags=["admin"])


@router.get("", response_model=list[TicketRead])
def list_queue(
    status: TicketStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> list[TicketRead]:
    tickets = ticket_service.list_tickets_for_queue(db, status)
    return [TicketRead.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> TicketRead:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    return TicketRead.model_validate(ticket)


@router.patch("/{ticket_id}/status", response_model=TicketRead)
def update_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> TicketRead:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    if payload.status not in ADMIN_SETTABLE_STATUSES:
        raise AppError(f"Admins cannot set status to '{payload.status.value}' directly")
    ticket = ticket_service.update_status(db, ticket, payload.status, payload.note, changed_by=admin.name)
    return TicketRead.model_validate(ticket)
