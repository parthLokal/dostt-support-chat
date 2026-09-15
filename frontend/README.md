# Dostt Support Chatbot — Frontend

The account-facing chat webview. Plain HTML/CSS/JS, no build step, no framework — matches the
"Python only" constraint on the rest of this project (no separate Node/React app). All business
logic (FAQ matching, refund automation, ticket rules, safety fallbacks) lives in the backend now;
this is a thin client.

Served by the backend itself (`backend/app/main.py` mounts this directory at `/`) — just run the
backend (see the repo root README) and open `http://localhost:8000/`.

Full-height, single-column, mobile-first layout — no demo chrome (persona picker, phone-frame
mockup) in the UI itself, matching how the real AstroHelp sibling project's chat webview looks:
just the chat.

## Switching demo accounts

Six seeded demo accounts exist (`backend/scripts/seed.py`) to exercise different points on the
refund-automation rules. Pick one via the `user_id` query param — the same handoff shape the real
Dostt app would use, and the same convention AstroHelp's chat-app uses for astrologers:

| user_id | Persona |
|---|---|
| `90001` (default) | First-ever ticket, no history |
| `90002` | Abuse pattern — 65% genuine-ticket ratio (blocked by the 70% rule) |
| `90003` | Mid spend, 85% genuine ticket history |
| `90004` | High spend, 90% genuine ticket history |
| `90005` | VIP spender (LTV > ₹15,000) |
| `90006` | Listener (Super Dostt) |

e.g. `http://localhost:8000/?user_id=90004`.

## Files

```
index.html   page shell — header, message area, composer
css/styles.css   flat, dark theme (tokens from /shared/tokens.css)
js/data.js       UI strings (i18n)
js/api.js        fetch wrapper for the backend API
js/app.js        chat state machine + rendering
```

## Talking to a different backend origin

`js/api.js`'s `API_BASE` is `""` (relative), which only works when this frontend is served by the
same FastAPI instance as the API (the default). If you serve these files separately (e.g. a
live-reload dev server on a different port), set `API_BASE` to the backend's full origin, e.g.
`"http://localhost:8000"`, and add that origin to `CORS_ORIGINS` in `backend/.env`.
