# Builds the FastAPI backend, which also serves frontend/ (the account-facing
# chat webview) and admin/ (the CS ticket-queue dashboard) as static files —
# see backend/app/main.py's FRONTEND_DIR/ADMIN_DIR/SHARED_DIR, all resolved
# two directories up from app/main.py. That's why this Dockerfile's build
# context is the repo root (not backend/) and copies all four top-level
# dirs into the same relative layout inside the image, not just backend/.
#
# Build (from the repo root): docker build -t dostt-support-backend .
# Run:   docker run -p 8000:8000 --env-file backend/.env dostt-support-backend
#   (only real settings, never GEMINI_VERTEX_CREDENTIALS_JSON etc. baked into
#   the image itself — see .dockerignore, which excludes backend/.env from
#   the build context entirely; pass it at `docker run`/deploy time instead.)
FROM python:3.12-slim

WORKDIR /app

# Dependencies first, so this layer only rebuilds when requirements.txt
# actually changes rather than on every code edit.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY frontend frontend
COPY admin admin
COPY shared shared

WORKDIR /app/backend

EXPOSE 8000

# Single worker, deliberately: app/core/rate_limit.py's chat/session-init
# rate limiter is in-process memory, not Redis-backed, since nothing here
# runs as more than one process yet. Running multiple workers (or replicas)
# would silently multiply every configured rate limit by the process count
# — move the limiter to a shared store first if you ever need to scale this
# past one worker/instance.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
