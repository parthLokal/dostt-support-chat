from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.agent import orchestrator
from app.agent.client import get_agent_client
from app.agent.context import SessionContext
from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.rate_limit import check_rate_limit, client_ip
from app.data.fallbacks import check_fallbacks
from app.db.session import get_db
from app.models.account import Account
from app.schemas.chat import ChatRequest, ChatResponse, TraceStepOut
from app.services import chat_session_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def send_message(payload: ChatRequest, request: Request, db: Session = Depends(get_db)) -> ChatResponse:
    # Checked before touching the DB or Gemini at all — see
    # app/core/rate_limit.py for why this is per-session AND per-IP.
    check_rate_limit("chat_session", payload.session_id, limit=settings.RATE_LIMIT_CHAT_PER_SESSION_PER_MIN)
    check_rate_limit("chat_ip", client_ip(request), limit=settings.RATE_LIMIT_CHAT_PER_IP_PER_MIN)

    session = chat_session_service.get_session(db, payload.session_id)
    if session is None:
        raise NotFoundError("Unknown session_id — call /api/session/init first")
    account = db.get(Account, session.account_id)
    if account is None:
        raise NotFoundError("Account not found for this session")

    chat_session_service.append_message(db, session.id, "user", payload.message)

    # Checked BEFORE any Gemini call, deterministically in code — the
    # chatbot PRD requires the mental-health category specifically be
    # "instant, no AI round-trip", and the same reasoning applies to every
    # other sensitive/off-topic category here: none of these are something
    # instruction-following alone should be trusted to catch every time.
    fallback = check_fallbacks(payload.message)
    if fallback is not None:
        chat_session_service.append_message(db, session.id, "assistant", fallback.response)
        return ChatResponse(reply=fallback.response, trace=[], metadata={"session_ended": fallback.ends_session})

    ctx = SessionContext(
        account_id=account.id,
        name=account.name,
        role=account.role.value,
        language=session.language,
        db=db,
        session_id=session.id,
        ticket_count_this_session=session.ticket_count,
        auth_token=payload.auth_token,
        language_id=payload.language_id,
        user_type_code=payload.user_type_code,
        country_code=payload.country_code,
        app_version=payload.app_version,
    )
    history = [orchestrator.HistoryTurn(role=t.role, text=t.text) for t in payload.history]
    client = get_agent_client()
    result = orchestrator.run_chat_turn(client, ctx, payload.message, history=history)

    chat_session_service.append_message(db, session.id, "assistant", result.reply)
    return ChatResponse(
        reply=result.reply,
        trace=[TraceStepOut(tool=s.tool, ok=s.ok, summary=s.summary) for s in result.trace],
        metadata=result.metadata,
    )
