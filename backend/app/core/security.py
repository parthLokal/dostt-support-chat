"""Admin dashboard auth only. There's nothing to sign on the astrologer-app
equivalent side (accounts) — see api/routes/session.py's docstring: the main
Dostt app is assumed to hand off a plain, already-authenticated account_id,
the same handoff shape AstroHelp uses for astrologers.
"""

from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.time import utcnow

_ALGORITHM = "HS256"


def issue_admin_token(admin_id: int) -> str:
    payload = {
        "admin_id": admin_id,
        "exp": utcnow() + timedelta(hours=settings.ADMIN_SESSION_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.ADMIN_SESSION_SECRET, algorithm=_ALGORITHM)


def decode_admin_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.ADMIN_SESSION_SECRET, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("admin_id")
