import enum


class AccountRole(str, enum.Enum):
    USER = "user"
    LISTENER = "listener"


# The real Dostt backend's own `user_type` claim/field — only USER=0 is
# actually confirmed (decoded from a real access token, 2026-09-08).
# LISTENER=1 is a reasonable, unconfirmed best guess (never seen a real
# Listener's token). Used both to derive a ticket's `user_type` field
# (ticket_service.py) and, in reverse, to guess an auto-created Account's
# role from a `user_type_code` if one is ever supplied (api/routes/session.py).
USER_TYPE_CODE_BY_ROLE: dict[AccountRole, int] = {
    AccountRole.USER: 0,
    AccountRole.LISTENER: 1,
}


class TicketStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# Statuses an admin may move a ticket to manually from the dashboard.
# SUBMITTED and ASSIGNED are only ever set automatically on ticket creation.
ADMIN_SETTABLE_STATUSES = (
    TicketStatus.IN_PROGRESS,
    TicketStatus.RESOLVED,
    TicketStatus.CLOSED,
)


class SessionResolution(str, enum.Enum):
    """How a ChatSession ended, for the PRD's fallback/escalation-rate metrics."""

    BOT = "bot"
    ESCALATED = "escalated"
