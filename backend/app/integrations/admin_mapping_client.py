"""Round-robins over whichever admins currently exist in our `admins` table —
deliberately not hardcoded ids, so a fresh database (or one with admins
deactivated/added via scripts/create_admin.py) always routes to whoever is
actually there instead of failing on an id that no longer exists. To go
live: replace with a real roster/ops API call.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin import Admin


def assign_admin(db: Session, ticket_count_so_far: int) -> Admin | None:
    admins = db.execute(select(Admin).where(Admin.is_active.is_(True)).order_by(Admin.id)).scalars().all()
    if not admins:
        return None
    return admins[ticket_count_so_far % len(admins)]
