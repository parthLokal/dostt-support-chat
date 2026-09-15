from pydantic import BaseModel


class HistoryTurnIn(BaseModel):
    role: str  # "account" | "assistant"
    text: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: list[HistoryTurnIn] = []
    # For the real Dostt ticket-creation API — re-sent on every call rather
    # than stored server-side (see agent/context.SessionContext's docstring).
    # All optional: absent until the app-side hand-off lands.
    auth_token: str | None = None
    language_id: int | None = None
    user_type_code: int | None = None
    country_code: str | None = None
    # The host app's own real app version (e.g. "1.1.38") — overrides the
    # hardcoded DOSTT_APP_VERSION default when present. See ?version= in
    # the webview hand-off URL, confirmed 2026-09-11.
    app_version: str | None = None


class TraceStepOut(BaseModel):
    tool: str
    ok: bool
    summary: str


class ChatResponse(BaseModel):
    reply: str
    trace: list[TraceStepOut]
    metadata: dict = {}


class SessionInitResponse(BaseModel):
    session_id: str
    account_id: int
    name: str
    role: str
    language: str


class CallOut(BaseModel):
    id: int
    call_type: str
    duration_sec: int
    coins_debited: int
    counterpart_name: str


class TransactionOut(BaseModel):
    id: int
    kind: str
    amount_inr: int
    coins: int
    status: str


class FaqOut(BaseModel):
    id: str
    category: str
    sub_issue: str
    landing_category: str | None
