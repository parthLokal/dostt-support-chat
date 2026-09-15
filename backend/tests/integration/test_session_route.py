def test_init_session_resolves_seeded_account(client, account):
    resp = client.get(f"/api/session/init?user_id={account.user_id}&language=en")
    assert resp.status_code == 200
    body = resp.json()
    assert body["account_id"] == account.id
    assert body["name"] == account.name
    assert body["role"] == "user"
    assert body["session_id"]


def test_init_session_unknown_user_id_is_404(client):
    resp = client.get("/api/session/init?user_id=does-not-exist")
    assert resp.status_code == 404


def test_init_session_decodes_base64_banner_user_id(client, account):
    # base64("90001") == "OTAwMDE=" — the real banner's atob()/parseInt()
    # decode, mirrored server-side (see _decode_banner_user_id).
    resp = client.get("/api/session/init?user_id=OTAwMDE=&language=en")
    assert resp.status_code == 200
    assert resp.json()["account_id"] == account.id


def test_init_session_auto_creates_account_for_new_real_user_id(client):
    resp = client.get("/api/session/init?user_id=172919381&language=en")
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "user"  # default, no user_type_code given
    assert body["name"]


def test_init_session_auto_created_account_uses_user_type_code(client):
    resp = client.get("/api/session/init?user_id=555000111&language=en&user_type_code=1")
    assert resp.status_code == 200
    assert resp.json()["role"] == "listener"


def test_init_session_auto_create_is_idempotent(client):
    first = client.get("/api/session/init?user_id=888777666&language=en")
    second = client.get("/api/session/init?user_id=888777666&language=en")
    assert first.json()["account_id"] == second.json()["account_id"]


def test_new_account_uses_real_redash_role_when_not_mocked(client, db, monkeypatch):
    import app.api.routes.session as session_route
    from sqlalchemy import select

    from app.models.account import Account

    monkeypatch.setattr(session_route, "MOCK_MODE", False)
    monkeypatch.setattr(
        session_route.redash_client, "run_query",
        lambda *a, **kw: [{"role": "listener", "profile_id": 42, "language_id": 1}],
    )

    resp = client.get("/api/session/init?user_id=16858575&language=en")
    assert resp.status_code == 200
    assert resp.json()["role"] == "listener"

    account = db.execute(select(Account).where(Account.user_id == "16858575")).scalar_one()
    assert account.onboarded_language_id == 1


def test_new_account_language_id_is_none_when_lookup_omits_it(client, db, monkeypatch):
    import app.api.routes.session as session_route
    from sqlalchemy import select

    from app.models.account import Account

    monkeypatch.setattr(session_route, "MOCK_MODE", False)
    monkeypatch.setattr(
        session_route.redash_client, "run_query",
        lambda *a, **kw: [{"role": "user", "profile_id": 7}],  # Listener-only accounts get no language_id
    )

    resp = client.get("/api/session/init?user_id=555222333&language=en")
    assert resp.status_code == 200

    account = db.execute(select(Account).where(Account.user_id == "555222333")).scalar_one()
    assert account.onboarded_language_id is None


def test_init_session_survives_concurrent_account_creation_race(client, monkeypatch):
    # Reproduces a real bug found 2026-09-10: two requests for the same
    # brand-new user_id arriving close together (e.g. a slow page load
    # reloaded) both see "no account yet" and both try to create one — the
    # loser used to 500 on the unique-constraint violation instead of
    # falling back to the row the winner already committed.
    import app.api.routes.session as session_route
    from app.models.account import Account
    from app.models.enums import AccountRole
    from sqlalchemy.exc import IntegrityError

    def racy_create(db_, user_id, language, user_type_code):
        winner = Account(user_id=user_id, name="Dostt User", role=AccountRole.USER, preferred_language=language)
        db_.add(winner)
        db_.commit()
        raise IntegrityError("INSERT", {}, Exception("duplicate key value violates unique constraint"))

    monkeypatch.setattr(session_route, "_create_account_for_real_user", racy_create)

    resp = client.get("/api/session/init?user_id=777000111&language=en")
    assert resp.status_code == 200
    assert resp.json()["role"] == "user"


def test_new_account_falls_back_when_redash_lookup_fails(client, monkeypatch):
    import app.api.routes.session as session_route

    monkeypatch.setattr(session_route, "MOCK_MODE", False)

    def boom(*a, **kw):
        raise RuntimeError("redash down")

    monkeypatch.setattr(session_route.redash_client, "run_query", boom)

    resp = client.get("/api/session/init?user_id=16858576&language=en&user_type_code=1")
    assert resp.status_code == 200
    assert resp.json()["role"] == "listener"  # falls back to user_type_code guess, not an error
