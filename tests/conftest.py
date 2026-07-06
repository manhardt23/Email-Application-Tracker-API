"""
Shared pytest fixtures available to all tests.

Provides a SQLite in-memory engine + session + seeded FastAPI test client
so individual test modules don't each re-create the same boilerplate.

Usage in a test file:
    def test_something(client, db):
        ...

The ``fresh_db`` fixture is autouse=False here — tests that want a clean
slate each invocation should request it explicitly or mark their module.

Auth notes
----------
The ``app`` fixture bypasses JWT auth by overriding ``get_current_user``
and ``require_admin`` with stubs.  Tests that want to exercise auth
behaviour (401/403) should build their own app without these overrides
or use the ``authed_client`` / ``viewer_client`` helpers from conftest.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import applications as apps_module
from app.api.v1 import dashboard as dashboard_module
from app.api.v1 import emails as emails_module
from app.api.v1 import jobs as jobs_module
from app.api.v1.router import api_router
from app.api.v1.stats import router as stats_router
from app.auth import dependencies as auth_deps
from app.db.models import Base, User
from app.middleware.rate_limit import limiter

# Disable rate limiting for the test suite (routes still carry decorators).
limiter.enabled = False

# ---------------------------------------------------------------------------
# Shared in-memory SQLite engine
# StaticPool: all sessions share one connection so schema persists per test.
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"

_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _override_get_db():
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


# Stub users returned by auth dependency overrides
_ADMIN_USER = User(id=1, username="admin", password_hash="x", role="admin")
_VIEWER_USER = User(id=2, username="viewer", password_hash="x", role="viewer")


def _override_get_current_user():
    return _ADMIN_USER


def _override_require_admin():
    return _ADMIN_USER


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fresh_db():
    """Create all tables before the test, drop them after."""
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def db(fresh_db):  # noqa: ARG001
    """Yield an open SQLAlchemy session backed by the in-memory SQLite DB."""
    session = _TestingSession()
    yield session
    session.close()


@pytest.fixture()
def app(fresh_db):  # noqa: ARG001
    """FastAPI app with all v1 routes, DB and auth dependencies overridden."""
    _app = FastAPI()
    _app.include_router(api_router, prefix="/api/v1")
    _app.include_router(stats_router, prefix="/stats", tags=["stats"])
    _app.dependency_overrides[apps_module.get_db] = _override_get_db
    _app.dependency_overrides[dashboard_module.get_db] = _override_get_db
    _app.dependency_overrides[emails_module.get_db] = _override_get_db
    _app.dependency_overrides[jobs_module.get_db] = _override_get_db
    _app.dependency_overrides[auth_deps.get_db] = _override_get_db
    _app.dependency_overrides[auth_deps.get_current_user] = _override_get_current_user
    _app.dependency_overrides[auth_deps.require_admin] = _override_require_admin
    return _app


@pytest.fixture()
def client(app):
    """Synchronous TestClient for the overridden FastAPI app."""
    return TestClient(app)
