"""
Shared pytest fixtures available to all tests.

Provides a SQLite in-memory engine + session + seeded FastAPI test client
so individual test modules don't each re-create the same boilerplate.

Usage in a test file:
    def test_something(client, db):
        ...

The ``fresh_db`` fixture is autouse=False here — tests that want a clean
slate each invocation should request it explicitly or mark their module.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import applications as apps_module
from app.api.v1 import emails as emails_module
from app.api.v1 import jobs as jobs_module
from app.api.v1.router import api_router
from app.db.models import Base

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
    """FastAPI app with all v1 routes and DB dependency overridden to SQLite."""
    _app = FastAPI()
    _app.include_router(api_router, prefix="/api/v1")
    _app.dependency_overrides[apps_module.get_db] = _override_get_db
    _app.dependency_overrides[emails_module.get_db] = _override_get_db
    _app.dependency_overrides[jobs_module.get_db] = _override_get_db
    return _app


@pytest.fixture()
def client(app):
    """Synchronous TestClient for the overridden FastAPI app."""
    return TestClient(app)
