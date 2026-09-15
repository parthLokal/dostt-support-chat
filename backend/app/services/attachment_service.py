"""Session-scoped pending ticket attachments — an account can attach a
screenshot in chat before create_support_ticket actually fires; this holds
onto it (DB-backed, see models/session_attachment.py) until that happens.

Upload flow: api/routes/attachments.py -> save_pending_attachment() (this
file) -> tool_registry._handle_create_support_ticket calls
consume_pending_attachment() when a ticket is actually raised, which hands
the file off to ticket_service (persisted permanently on the Ticket row via
attachment_path) and clears the "pending" row so it isn't reused for an
unrelated, later ticket in the same session.
"""

import logging
import os
import uuid
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.session_attachment import SessionAttachment

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConsumedAttachment:
    file_path: str
    content_type: str


class AttachmentError(ValueError):
    pass


def _ensure_upload_dir() -> str:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    return settings.UPLOAD_DIR


def _extension_for(content_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/heic": ".heic",
    }.get(content_type, "")


def save_pending_attachment(db: Session, session_id: str, file: UploadFile, data: bytes) -> SessionAttachment:
    if file.content_type not in settings.upload_allowed_content_types_list:
        raise AttachmentError(f"Unsupported file type '{file.content_type}'")
    if len(data) > settings.UPLOAD_MAX_BYTES:
        raise AttachmentError(f"File too large — max {settings.UPLOAD_MAX_BYTES // (1024 * 1024)}MB")

    upload_dir = _ensure_upload_dir()
    # A random filename — never derived from the client-supplied name/session
    # id — is what keeps this safe against path traversal, regardless of
    # whatever the browser sends as the original filename.
    disk_name = f"{uuid.uuid4().hex}{_extension_for(file.content_type)}"
    file_path = os.path.join(upload_dir, disk_name)
    with open(file_path, "wb") as fh:
        fh.write(data)

    existing = db.execute(
        select(SessionAttachment).where(SessionAttachment.session_id == session_id)
    ).scalar_one_or_none()
    if existing is not None:
        _delete_file_quietly(existing.file_path)
        db.delete(existing)
        db.flush()

    attachment = SessionAttachment(
        session_id=session_id,
        file_path=file_path,
        content_type=file.content_type,
        original_filename=file.filename or "upload",
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def get_pending_attachment(db: Session, session_id: str) -> SessionAttachment | None:
    return db.execute(
        select(SessionAttachment).where(SessionAttachment.session_id == session_id)
    ).scalar_one_or_none()


def clear_pending_attachment(db: Session, session_id: str) -> bool:
    """For an explicit user 'remove attachment' action — unlike
    consume_pending_attachment, this deletes the file too, since nothing
    will ever reference it afterward."""
    attachment = get_pending_attachment(db, session_id)
    if attachment is None:
        return False
    _delete_file_quietly(attachment.file_path)
    db.delete(attachment)
    db.commit()
    return True


def consume_pending_attachment(db: Session, session_id: str) -> ConsumedAttachment | None:
    """Detaches (deletes) the pending row but leaves the file on disk — the
    caller (ticket_service) is expected to persist file_path on the Ticket
    it's creating right now. Returns a plain dataclass, not the ORM row —
    the row is expired past this point since it's deleted immediately."""
    attachment = get_pending_attachment(db, session_id)
    if attachment is None:
        return None
    result = ConsumedAttachment(file_path=attachment.file_path, content_type=attachment.content_type)
    db.delete(attachment)
    db.commit()
    return result


def _delete_file_quietly(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        logger.warning("Could not remove replaced attachment file %s", path)
