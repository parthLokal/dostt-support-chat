import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import attachments, calls, chat, faqs, session, tickets, transactions
from app.api.routes.admin import login as admin_login
from app.api.routes.admin import tickets as admin_tickets
from app.core.config import assert_admin_secrets_are_safe, settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

# Without this, Python's root logger defaults to WARNING with no configured
# handler — every logger.info(...) call anywhere in the app (including the
# ticket real-API-mirror diagnostics in ticket_service.py, added 2026-09-16
# specifically to make silent no-ops debuggable) is silently dropped rather
# than reaching stdout, regardless of whether the surrounding
# infra/log-viewer is otherwise working correctly. This was a real
# contributing factor, not just an infra/log-viewer issue, the last few
# times pod logs appeared to show nothing at all.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

assert_admin_secrets_are_safe(settings)

# The chat webview and the admin dashboard are both plain static
# HTML/CSS/JS (no build step, no separate Node app — see README) — served
# directly by FastAPI rather than a second frontend service, per "Python
# only". frontend/ holds the account-facing chat UI; admin/ holds the CS
# ticket-queue dashboard.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
ADMIN_DIR = Path(__file__).resolve().parents[2] / "admin"
# Design tokens (colors/type/radii) shared by both frontends — see its own
# header comment for why this lives outside either app's directory.
SHARED_DIR = Path(__file__).resolve().parents[2] / "shared"

app = FastAPI(title="Dostt Support Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Without this, an unhandled exception propagates past CORSMiddleware
    # entirely (Starlette's ServerErrorMiddleware sits outside it), so the
    # browser reports a confusing "CORS blocked" error instead of the real
    # failure. Catching it here keeps the response inside the CORS-wrapped
    # layer and gives the frontend a real (if generic) error body to show.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


app.include_router(session.router)
app.include_router(attachments.router)
app.include_router(calls.router)
app.include_router(transactions.router)
app.include_router(faqs.router)
app.include_router(chat.router)
app.include_router(tickets.router)
app.include_router(admin_login.router)
app.include_router(admin_tickets.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if SHARED_DIR.exists():
    app.mount("/shared", StaticFiles(directory=str(SHARED_DIR)), name="shared")

if ADMIN_DIR.exists():
    app.mount("/admin", StaticFiles(directory=str(ADMIN_DIR), html=True), name="admin")

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
