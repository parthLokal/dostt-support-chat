"""Provision a new admin (dashboard access). Every admin logs in with the
single fixed ADMIN_PASSWORD (see core/config.py) — there is no per-admin
password. Usage:

    python -m scripts.create_admin "CS Lead Name" cs-lead@getlokalapp.com
"""

import sys

from app.db.session import SessionLocal
from app.models.admin import Admin


def run(name: str, email: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(Admin).filter_by(email=email).one_or_none()
        if existing:
            existing.is_active = True
            existing.name = name
            db.commit()
            print(f"Reactivated existing admin '{email}'")
            return
        db.add(Admin(name=name, email=email, is_active=True))
        db.commit()
        print(f"Created admin '{name}' <{email}>")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.create_admin <name> <email>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
