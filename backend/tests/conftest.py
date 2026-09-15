import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import session as session_route
from app.core import rate_limit
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.integrations import call_client, transaction_client
from app.main import app
from app.models.account import Account
from app.models.admin import Admin
from app.models.call import Call
from app.models.enums import AccountRole

test_engine = create_engine(settings.TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def _reset_schema():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture(autouse=True)
def _isolated_upload_dir(tmp_path, monkeypatch):
    # Never let a test write into the real uploads/ dir on disk.
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))


@pytest.fixture(autouse=True)
def _default_mock_mode_true(monkeypatch):
    # The test suite must never depend on whatever MOCK_MODE happens to be
    # set to in a developer's local .env (bug found 2026-09-10: flipping
    # MOCK_MODE=false locally to test against real data silently broke
    # unrelated tests that assumed the mocked-fallback behavior). Every
    # module that reads MOCK_MODE bound its own copy at import time (`from
    # app.integrations.config import MOCK_MODE`), so each needs patching
    # individually — a test that wants the real-data path still explicitly
    # monkeypatches it to False itself, same as before; this fixture only
    # fixes the *default*.
    for module in (call_client, transaction_client, session_route):
        monkeypatch.setattr(module, "MOCK_MODE", True)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    # Every TestClient request shares the same fake client IP, so the
    # per-IP counter (app/core/rate_limit.py) would otherwise accumulate
    # across the whole test run instead of resetting per test.
    rate_limit.reset_for_tests()
    yield


@pytest.fixture
def db() -> Session:
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def account(db) -> Account:
    acc = Account(
        user_id="90001", name="Priya", role=AccountRole.USER,
        ltv_value_inr=2500, tickets_raised=10, refunded_tickets=8,
        ltv_coins=5000, refund_coins_lifetime=500,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


@pytest.fixture
def listener_account(db) -> Account:
    acc = Account(
        user_id="90006", name="Ananya", role=AccountRole.LISTENER,
        ltv_value_inr=3000, tickets_raised=6, refunded_tickets=5,
        ltv_coins=12000, refund_coins_lifetime=300,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


@pytest.fixture
def call(db, account) -> Call:
    c = Call(account_id=account.id, call_type="audio", duration_sec=35, coins_debited=30, counterpart_name="Meera")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture
def admin(db) -> Admin:
    a = Admin(name="Test Admin", email="test-admin@getlokalapp.com")
    db.add(a)
    db.commit()
    db.refresh(a)
    return a
