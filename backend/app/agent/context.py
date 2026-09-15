from dataclasses import dataclass

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class SessionContext:
    """Everything a tool handler is allowed to know about who's asking.

    account_id comes from the verified session handoff (see
    api/routes/session.py), never from a request body or from anything the
    model supplies — this is the only account_id a tool handler should ever
    use. See agent/executor.py for where a model-supplied account_id (if any)
    gets discarded.

    ticket_count_this_session gates the chatbot PRD's 2-ticket-per-session
    cap — a purely mechanical fact about the conversation so far, not
    something the model is trusted to self-police (instruction-following
    isn't 100% reliable, same reasoning AstroHelp's has_prior_reply flag
    documents for its own escalation gate).

    auth_token / language_id / user_type_code / country_code / app_version
    are for the real Dostt ticket-creation API (app/integrations/dostt_api_client.py)
    — never persisted anywhere (not on Account, not on ChatSession), re-sent
    by the frontend on every /api/chat call the same way `history` already
    is. auth_token comes from the real webview hand-off (confirmed
    2026-09-11: ?userId=&token=&version= — note the URL param names differ
    from these field names); language_id/user_type_code/country_code are
    usually derived from auth_token's own claims instead of sent explicitly
    (see ticket_service._mirror_to_real_api). All optional — their absence
    just means ticket_service falls back to local-only ticket creation, not
    an error.
    """

    account_id: int
    name: str
    role: str  # "user" | "listener"
    language: str
    db: Session
    session_id: str
    ticket_count_this_session: int = 0
    auth_token: str | None = None
    language_id: int | None = None
    user_type_code: int | None = None
    country_code: str | None = None
    app_version: str | None = None
