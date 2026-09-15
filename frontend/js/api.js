/* ---------------------------------------------------------------------
   Thin fetch wrapper for the Python backend (backend/app/). Relative URLs
   work out of the box when this frontend is served BY that backend (see
   backend/app/main.py's StaticFiles mount) — same origin, no CORS needed.
   If you serve this frontend separately (e.g. a live-reload dev server),
   set API_BASE to the backend's origin, e.g. "http://localhost:8000".
--------------------------------------------------------------------- */
const API_BASE = "";

class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Request failed (${status})`);
    this.status = status;
  }
}

async function apiGet(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail);
  }
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errBody.detail);
  }
  return res.json();
}

async function uploadAttachment(sessionId, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/session/${sessionId}/attachment`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail);
  }
  return res.json();
}

const api = {
  initSession: (userId, language) => apiGet(`/api/session/init?user_id=${encodeURIComponent(userId)}&language=${encodeURIComponent(language)}`),
  recentCalls: (accountId) => apiGet(`/api/calls?account_id=${accountId}`),
  recentTransactions: (accountId, kind) => apiGet(`/api/transactions?account_id=${accountId}&kind=${kind}`),
  faqs: (landingCategory, audience) => apiGet(`/api/faqs?landing_category=${landingCategory}&audience=${audience}`),
  sendChat: (sessionId, message, history, authToken, appVersion) =>
    apiPost("/api/chat", {
      session_id: sessionId, message, history,
      auth_token: authToken || undefined,
      app_version: appVersion || undefined,
    }),
  myTickets: (accountId) => apiGet(`/api/tickets?account_id=${accountId}`),
  uploadAttachment,
};
