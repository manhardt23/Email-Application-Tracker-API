"""
Phase 13 auth tests — unit tests for hashing + JWT, integration tests for
login endpoint, protected routes (401/403), and RBAC enforcement.
"""
from unittest.mock import patch
from uuid import uuid4

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
from app.api.v1.stats import router as stats_router
from app.auth import dependencies as auth_deps
from app.auth.hashing import hash_password, verify_password
from app.auth.jwt_handler import create_access_token, decode_access_token
from app.db.models import Base, User
from app.db.repositories.user_repo import UserRepository

# ---------------------------------------------------------------------------
# In-memory DB for auth tests
# ---------------------------------------------------------------------------

_engine = create_engine(
    "sqlite:///:memory:",
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


@pytest.fixture(autouse=True)
def _fresh_schema():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def db():
    session = _TestingSession()
    yield session
    session.close()


def _make_app(*, auth_override: bool = False):
    """Build a test app. auth_override=True bypasses JWT (as prod routes need tokens)."""
    _app = FastAPI()
    _app.include_router(api_router, prefix="/api/v1")
    _app.include_router(stats_router, prefix="/stats", tags=["stats"])
    _app.dependency_overrides[apps_module.get_db] = _override_get_db
    _app.dependency_overrides[emails_module.get_db] = _override_get_db
    _app.dependency_overrides[jobs_module.get_db] = _override_get_db
    _app.dependency_overrides[auth_deps.get_db] = _override_get_db
    if auth_override:
        admin = User(id=1, username="admin", password_hash="x", role="admin")
        _app.dependency_overrides[auth_deps.get_current_user] = lambda: admin
        _app.dependency_overrides[auth_deps.require_admin] = lambda: admin
    return _app


@pytest.fixture()
def live_client():
    """TestClient with NO auth bypass — real JWT validation active."""
    return TestClient(_make_app(auth_override=False), raise_server_exceptions=True)


@pytest.fixture()
def admin_client():
    """TestClient with auth bypassed as admin (for non-auth tests)."""
    return TestClient(_make_app(auth_override=True))


# ---------------------------------------------------------------------------
# Unit: hashing
# ---------------------------------------------------------------------------


def test_hash_password_is_not_plain():
    hashed = hash_password("secret")
    assert hashed != "secret"


def test_verify_password_correct():
    hashed = hash_password("secret")
    assert verify_password("secret", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("secret")
    assert verify_password("wrong", hashed) is False


def test_hash_is_different_each_call():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2


# ---------------------------------------------------------------------------
# Unit: JWT
# ---------------------------------------------------------------------------


def test_create_and_decode_token():
    token = create_access_token("alice", "admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "alice"
    assert payload["role"] == "admin"


def test_decode_token_expired():
    from jose import JWTError

    test_jwt_signing_key = f"unit-test-jwt-key-{uuid4().hex}"

    with patch("app.auth.jwt_handler.get_settings") as mock_gs:
        s = mock_gs.return_value
        s.jwt_secret = test_jwt_signing_key
        s.jwt_algorithm = "HS256"
        s.jwt_expiry_minutes = -1  # already expired
        token = create_access_token("bob", "viewer")

    with patch("app.auth.jwt_handler.get_settings") as mock_gs2:
        s2 = mock_gs2.return_value
        s2.jwt_secret = test_jwt_signing_key
        s2.jwt_algorithm = "HS256"
        with pytest.raises(JWTError):
            decode_access_token(token)


def test_decode_malformed_token():
    from jose import JWTError

    with pytest.raises(JWTError):
        decode_access_token("not.a.token")


# ---------------------------------------------------------------------------
# Integration: POST /auth/login
# ---------------------------------------------------------------------------


def test_login_returns_token(db, live_client):
    repo = UserRepository(db)
    repo.create("alice", hash_password("pass123"), "admin")
    db.commit()

    resp = live_client.post(
        "/api/v1/auth/login", data={"username": "alice", "password": "pass123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(db, live_client):
    repo = UserRepository(db)
    repo.create("alice", hash_password("pass123"), "admin")
    db.commit()

    resp = live_client.post(
        "/api/v1/auth/login", data={"username": "alice", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_login_unknown_user(live_client):
    resp = live_client.post(
        "/api/v1/auth/login", data={"username": "nobody", "password": "x"}
    )
    assert resp.status_code == 401


def test_login_does_not_reveal_username_existence(db, live_client):
    """Both wrong-user and wrong-password return identical 401 detail."""
    repo = UserRepository(db)
    repo.create("alice", hash_password("correct"), "admin")
    db.commit()

    r1 = live_client.post("/api/v1/auth/login", data={"username": "nobody", "password": "x"})
    r2 = live_client.post("/api/v1/auth/login", data={"username": "alice", "password": "bad"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]


# ---------------------------------------------------------------------------
# Integration: GET /auth/me
# ---------------------------------------------------------------------------


def test_me_returns_current_user(db, live_client):
    repo = UserRepository(db)
    repo.create("alice", hash_password("pass"), "viewer")
    db.commit()

    login = live_client.post("/api/v1/auth/login", data={"username": "alice", "password": "pass"})
    token = login.json()["access_token"]

    resp = live_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"username": "alice", "role": "viewer"}


def test_me_returns_401_without_token(live_client):
    resp = live_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Integration: protected routes return 401 without token
# ---------------------------------------------------------------------------


def test_get_applications_without_token_returns_401(live_client):
    resp = live_client.get("/api/v1/applications")
    assert resp.status_code == 401


def test_get_emails_without_token_returns_401(live_client):
    resp = live_client.get("/api/v1/emails")
    assert resp.status_code == 401


def test_get_jobs_without_token_returns_401(live_client):
    resp = live_client.get("/api/v1/jobs/1")
    assert resp.status_code == 401


def test_health_does_not_require_auth(live_client):
    resp = live_client.get("/api/v1/health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Integration: RBAC — viewer cannot call admin routes
# ---------------------------------------------------------------------------


def _viewer_token(db) -> str:
    repo = UserRepository(db)
    repo.create("viewer", hash_password("vpass"), "viewer")
    db.commit()
    return create_access_token("viewer", "viewer")


def _admin_token(db) -> str:
    repo = UserRepository(db)
    repo.create("admin", hash_password("apass"), "admin")
    db.commit()
    return create_access_token("admin", "admin")


def test_viewer_put_application_returns_403(db, live_client):
    token = _viewer_token(db)
    resp = live_client.put(
        "/api/v1/applications/1",
        json={"stage": "interview"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_viewer_trigger_email_check_returns_403(db, live_client):
    token = _viewer_token(db)
    resp = live_client.post(
        "/api/v1/jobs/email-check", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


def test_viewer_set_email_limit_returns_403(db, live_client):
    token = _viewer_token(db)
    resp = live_client.post(
        "/api/v1/jobs/email-limit",
        json={"max_emails_per_run": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_viewer_get_job_status_returns_403(db, live_client):
    token = _viewer_token(db)
    resp = live_client.get("/api/v1/jobs/1", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_can_trigger_email_check(db, live_client):
    token = _admin_token(db)
    with patch("app.api.v1.jobs._run_worker"):
        resp = live_client.post(
            "/api/v1/jobs/email-check", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 202


def test_viewer_get_emails_returns_403(db, live_client):
    token = _viewer_token(db)
    resp = live_client.get("/api/v1/emails", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_viewer_can_read_emails_review(db, live_client):
    token = _viewer_token(db)
    resp = live_client.get("/api/v1/emails/review", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_viewer_get_applications_returns_403(db, live_client):
    token = _viewer_token(db)
    resp = live_client.get("/api/v1/applications", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_can_list_applications(db, live_client):
    token = _admin_token(db)
    resp = live_client.get("/api/v1/applications", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 404)
