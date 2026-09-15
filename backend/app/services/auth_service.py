"""Admin login. No self-service signup or per-admin password reset — every
admin logs in with the single fixed ADMIN_PASSWORD (see core/config.py);
scripts/create_admin.py is the only way to add one. OWNER_EMAIL always works
even before any Admin row exists, solving the bootstrap chicken-and-egg
problem on a brand-new database — same convention as the AstroHelp sibling
project's _maybe_bootstrap_owner.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.models.admin import Admin


def _maybe_bootstrap_owner(db: Session) -> Admin:
    owner = db.execute(select(Admin).where(Admin.email == settings.OWNER_EMAIL)).scalar_one_or_none()
    if owner is None:
        owner = Admin(name="Owner", email=settings.OWNER_EMAIL, is_active=True)
        db.add(owner)
        db.commit()
        db.refresh(owner)
    elif not owner.is_active:
        owner.is_active = True
        db.commit()
    return owner


def login(db: Session, email: str, password: str) -> Admin:
    if password != settings.ADMIN_PASSWORD:
        raise UnauthorizedError("Incorrect email or password")

    if email == settings.OWNER_EMAIL:
        return _maybe_bootstrap_owner(db)

    admin = db.execute(
        select(Admin).where(Admin.email == email, Admin.is_active.is_(True))
    ).scalar_one_or_none()
    if admin is None:
        raise UnauthorizedError("Incorrect email or password")
    return admin
