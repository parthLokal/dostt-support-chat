"""Only the fallback path is tested at the HTTP layer here — it's checked
before the Gemini client is even constructed (see api/routes/chat.py), so it
needs no real GEMINI_VERTEX_CREDENTIALS_JSON. The full tool-calling loop is
covered at the unit level in test_agent_tool_selection.py against a real
executor, and the orchestrator's retry/finish_reason handling against a fake
AgentClient in test_orchestrator.py — neither needs live Gemini access either.
"""


def _init_session(client, user_id):
    resp = client.get(f"/api/session/init?user_id={user_id}&language=en")
    assert resp.status_code == 200
    return resp.json()["session_id"]


def test_mental_health_fallback_short_circuits_before_any_agent_call(client, account):
    session_id = _init_session(client, account.user_id)
    resp = client.post("/api/chat", json={"session_id": session_id, "message": "I want to end my life"})
    assert resp.status_code == 200
    body = resp.json()
    assert "Tele-MANAS" in body["reply"]
    assert body["trace"] == []


def test_underage_fallback_flags_session_ended(client, account):
    session_id = _init_session(client, account.user_id)
    resp = client.post("/api/chat", json={"session_id": session_id, "message": "I'm 16 years old"})
    assert resp.status_code == 200
    body = resp.json()
    assert "under 18" in body["reply"]
    assert body["metadata"]["session_ended"] is True


def test_unknown_session_id_is_404(client):
    resp = client.post("/api/chat", json={"session_id": "does-not-exist", "message": "hi"})
    assert resp.status_code == 404


def test_chat_is_rate_limited_per_session(client, account, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "RATE_LIMIT_CHAT_PER_SESSION_PER_MIN", 3)
    monkeypatch.setattr(settings, "RATE_LIMIT_CHAT_PER_IP_PER_MIN", 1000)  # isolate the per-session limit only
    session_id = _init_session(client, account.user_id)

    for _ in range(3):
        resp = client.post("/api/chat", json={"session_id": session_id, "message": "I'm 16 years old"})
        assert resp.status_code == 200

    resp = client.post("/api/chat", json={"session_id": session_id, "message": "I'm 16 years old"})
    assert resp.status_code == 429


def test_chat_is_rate_limited_per_ip(client, account, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "RATE_LIMIT_CHAT_PER_SESSION_PER_MIN", 1000)  # isolate the per-IP limit only
    monkeypatch.setattr(settings, "RATE_LIMIT_CHAT_PER_IP_PER_MIN", 2)

    session_a = _init_session(client, account.user_id)
    session_b = _init_session(client, account.user_id)
    fallback_msg = "I'm 16 years old"  # a fallback-pattern message — short-circuits before any Gemini call

    assert client.post("/api/chat", json={"session_id": session_a, "message": fallback_msg}).status_code == 200
    assert client.post("/api/chat", json={"session_id": session_b, "message": fallback_msg}).status_code == 200
    # Third request from the same (test) client IP, even under a different
    # session, trips the shared per-IP cap.
    resp = client.post("/api/chat", json={"session_id": session_a, "message": fallback_msg})
    assert resp.status_code == 429
