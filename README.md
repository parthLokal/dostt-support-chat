# Dostt Support Chatbot

An in-app AI support chatbot for Dostt (users and Listeners/Super Dostt). Built to mirror the
architecture and best practices of the **AstroHelp** sibling project (FastAPI + SQLAlchemy +
Alembic + Postgres, a Gemini tool-calling agent with a security-boundary executor,
services/integrations layering) — Python end to end, per request, rather than a separate
Node/React frontend.

## Architecture

```
backend/     FastAPI + SQLAlchemy + Alembic + Postgres, Gemini (Vertex AI) tool-calling agent
frontend/    Account-facing chat webview — plain HTML/CSS/JS, no build step
admin/       CS ticket-queue dashboard — plain HTML/CSS/JS, no build step
Dockerfile   Builds the backend image (also serves both frontends — see backend/app/main.py)
docker-compose.yml   Postgres, plus an optional `backend` service for exercising the real
                      container locally before deploying it anywhere
```

Both frontends are static files served directly by FastAPI (`StaticFiles` mounts in
`backend/app/main.py`) rather than a second Node service — same-origin, so no CORS
configuration is needed when running everything through the backend on one port.

Backend layering (see `backend/app/`), same shape as AstroHelp:

- `agent/` — the Gemini tool-calling orchestrator. Only imports `agent/tool_schemas.py` (pure
  data); never imports `integrations/` or `services/` directly.
- `agent/executor.py` — the one place that resolves a tool name to a handler and dispatches it.
  This is also the **security boundary**: it unconditionally strips whatever `account_id` the
  model supplied in a tool call and replaces it with the id from the verified session, before any
  handler runs. Handlers never trust an `account_id` from tool input — proven by
  `tests/unit/test_agent_tool_selection.py::test_account_id_in_tool_input_is_ignored_and_overridden`.
- `integrations/` — mocked external systems (Dostt's own: calls, transactions, admin
  round-robin, Slack), one file each, gated by `MOCK_MODE`.
- `services/` — cross-integration business logic. `refund_service.py` is the deterministic
  refund-automation engine (the v1.1 PRD's rules — no AI involved by design). `ticket_service.py`
  does create → auto-assign → Slack-notify in one transaction, and is the only module allowed to
  write `Ticket.status`.
- `api/routes/` — thin FastAPI route handlers that call into `services/`.

## What's real vs. mocked

Session init, recent calls/transactions, FAQ card listings, ticket creation/listing, the refund
decision engine, and the whole admin dashboard (login, ticket queue, status updates, history) are
all **fully live** — backed by real Postgres tables, no client-side logic, no Gemini needed. Try
them via `pytest` (52 tests, all passing) or by running the app (below).

`/api/chat` — the conversational agent itself — needs a real `GEMINI_VERTEX_CREDENTIALS_JSON` (a
GCP service-account credential) in `backend/.env`. Without one, it returns a graceful error and
the frontend shows a calm "not configured" message — same documented behavior as the AstroHelp
sibling project without its own Gemini key. The tool-calling loop, the account_id security
boundary, and every tool handler are all covered by unit tests against a **fake** Gemini client
(`tests/unit/test_orchestrator.py`, `tests/unit/test_agent_tool_selection.py`) and don't need a
real key to verify.

## Setup

### 1. Postgres

```bash
docker compose up -d
docker exec dostt-support-postgres psql -U dostt -d dostt_support -c "CREATE DATABASE dostt_support_test;"
```

### 2. Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python -m scripts.seed              # 6 demo accounts (5 users + 1 listener)
python -m scripts.create_admin "Your Name" you@getlokalapp.com
uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:8000/` for the chat webview (demo accounts `90001`-`90006` in the
left rail) and `http://localhost:8000/admin/` for the CS dashboard (log in with the email you
just created and `ADMIN_PASSWORD` from `.env`, default `dosttSupport@123`).

Tests and lint:

```bash
pytest
ruff check app scripts tests
```

## Refund automation

`app/services/refund_service.py` implements the "Revised Automated CS Refund Workflow v1.1" PRD
exactly: Very High LTV full-refund window, the unified <50s duration check for High/Mid/Low, the
70% genuine-ticket-history rule (skipped for first-time users), and the refund/LTV 20% spend cap.
Six seeded demo accounts (`scripts/seed.py`) span the interesting cases — a first-timer, a
repeat-abuse pattern (~65% genuine ratio, correctly blocked), two genuine-history accounts, a VIP,
and a Listener — so `tests/unit/test_refund_service.py` and the live `/api/calls` +
`check_refund_eligibility` tool can demonstrate the "refund more genuine users, block abusers"
tradeoff the PRD describes.
