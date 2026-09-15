from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import UnauthorizedError
from app.core.security import decode_admin_token
from app.db.session import get_db
from app.models.admin import Admin


def get_current_admin(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Admin:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header")
    admin_id = decode_admin_token(authorization.removeprefix("Bearer "))
    if admin_id is None:
        raise UnauthorizedError("Invalid or expired session")
    admin = db.get(Admin, admin_id)
    if admin is None or not admin.is_active:
        raise UnauthorizedError("Invalid or expired session")
    return admin
