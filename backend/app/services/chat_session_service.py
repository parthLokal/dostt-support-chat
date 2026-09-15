import uuid

from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.enums import SessionResolution


def start_session(db: Session, account_id: int, language: str) -> ChatSession:
    session = ChatSession(id=str(uuid.uuid4()), account_id=account_id, language=language)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: str) -> ChatSession | None:
    return db.get(ChatSession, session_id)


def append_message(db: Session, session_id: str, role: str, text: str) -> None:
    db.add(ChatMessage(session_id=session_id, role=role, text=text))
    db.commit()


def mark_resolved_by_bot(db: Session, session_id: str, *, category: str, sub_category: str) -> None:
    session = db.get(ChatSession, session_id)
    if session is None:
        return
    session.resolution = SessionResolution.BOT
    session.category = category
    session.sub_category = sub_category
    db.commit()


def mark_escalated(db: Session, session_id: str, *, ticket_id: int, category: str) -> None:
    session = db.get(ChatSession, session_id)
    if session is None:
        return
    session.resolution = SessionResolution.ESCALATED
    session.category = category
    session.ticket_count += 1
    db.commit()
