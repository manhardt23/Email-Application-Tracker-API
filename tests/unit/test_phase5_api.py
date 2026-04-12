"""
Phase 5 API tests — emails endpoints, applications PUT, jobs DB-backed.

Uses SQLite in-memory via dependency override so no real DB is needed.
"""
from datetime import datetime
from unittest.mock import patch

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
from app.db.models import Application, Base, Company, Email, EmailAnalysis, WorkerRun

# ---------------------------------------------------------------------------
# In-memory SQLite test DB + session factory
# StaticPool forces all sessions to share one connection so tables persist.
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"
_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def app():
    # Build a minimal FastAPI app — skip lifespan to avoid real DB creation.
    _app = FastAPI()
    _app.include_router(api_router, prefix="/api/v1")
    _app.dependency_overrides[apps_module.get_db] = override_get_db
    _app.dependency_overrides[emails_module.get_db] = override_get_db
    _app.dependency_overrides[jobs_module.get_db] = override_get_db
    return _app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def db():
    session = TestingSession()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_email_with_analysis(
    session,
    *,
    needs_review=False,
    is_application=True,
    message_id="msg-1",
    uid="uid-1",
):
    email = Email(
        message_id=message_id,
        uid=uid,
        sender="hr@example.com",
        subject="Your application",
        received_date=datetime(2024, 1, 1),
        body="body text",
    )
    session.add(email)
    session.flush()
    analysis = EmailAnalysis(
        email_id=email.id,
        is_application=is_application,
        detected_company="Acme",
        detected_position="Engineer",
        detected_stage="applied",
        confidence="high",
        needs_review=needs_review,
        model_used="test-model",
    )
    session.add(analysis)
    session.commit()
    return email


def _seed_application(session, stage="applied"):
    company = Company(name="Acme Corp")
    session.add(company)
    session.flush()
    application = Application(company_id=company.id, position="Engineer", stage=stage)
    session.add(application)
    session.commit()
    return application


# ---------------------------------------------------------------------------
# GET /emails
# ---------------------------------------------------------------------------

def test_list_emails_returns_flat_response(client, db):
    _seed_email_with_analysis(db)

    resp = client.get("/api/v1/emails")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    row = data[0]
    assert row["sender"] == "hr@example.com"
    assert row["is_application"] is True
    assert row["detected_company"] == "Acme"
    assert row["needs_review"] is False


def test_list_emails_404_when_empty(client):
    resp = client.get("/api/v1/emails")
    assert resp.status_code == 404


def test_list_emails_respects_limit(client, db):
    for i in range(3):
        _seed_email_with_analysis(db, message_id=f"msg-{i}", uid=f"uid-{i}")

    resp = client.get("/api/v1/emails?limit=2&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# GET /emails/review
# ---------------------------------------------------------------------------

def test_list_emails_review_returns_only_needs_review(client, db):
    _seed_email_with_analysis(db, needs_review=True)

    resp = client.get("/api/v1/emails/review")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["needs_review"] is True


def test_list_emails_review_404_when_none_need_review(client, db):
    _seed_email_with_analysis(db, needs_review=False)

    resp = client.get("/api/v1/emails/review")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /applications/{id}
# ---------------------------------------------------------------------------

def test_put_application_updates_stage(client, db):
    application = _seed_application(db, stage="applied")

    resp = client.put(f"/api/v1/applications/{application.id}", json={"stage": "interview"})

    assert resp.status_code == 200
    assert resp.json()["stage"] == "interview"


def test_put_application_updates_notes(client, db):
    application = _seed_application(db)

    resp = client.put(f"/api/v1/applications/{application.id}", json={"notes": "Great company"})

    assert resp.status_code == 200
    assert resp.json()["notes"] == "Great company"


def test_put_application_explicit_null_notes_clears(client, db):
    application = _seed_application(db)
    db.query(Application).filter(Application.id == application.id).update({"notes": "to clear"})
    db.commit()

    resp = client.put(f"/api/v1/applications/{application.id}", json={"notes": None})

    assert resp.status_code == 200
    assert resp.json()["notes"] is None


def test_put_application_rejects_null_stage(client, db):
    application = _seed_application(db)

    resp = client.put(f"/api/v1/applications/{application.id}", json={"stage": None})

    assert resp.status_code == 422


def test_put_application_rejects_invalid_stage(client, db):
    application = _seed_application(db)

    resp = client.put(f"/api/v1/applications/{application.id}", json={"stage": "ghosted"})

    assert resp.status_code == 422


def test_put_application_404_for_missing(client):
    resp = client.put("/api/v1/applications/9999", json={"stage": "offer"})
    assert resp.status_code == 404


def test_put_application_partial_update_no_fields(client, db):
    application = _seed_application(db, stage="applied")

    # Empty body — no changes, should still 200
    resp = client.put(f"/api/v1/applications/{application.id}", json={})

    assert resp.status_code == 200
    assert resp.json()["stage"] == "applied"


# ---------------------------------------------------------------------------
# POST /jobs/email-check and GET /jobs/{job_id}
# ---------------------------------------------------------------------------

def test_trigger_job_creates_worker_run(client):
    with patch("app.api.v1.jobs._run_worker") as mock_run:
        resp = client.post("/api/v1/jobs/email-check")

    mock_run.assert_called_once()
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "running"


def test_get_job_status_returns_run_fields(client, db):
    run = WorkerRun(status="completed", emails_fetched=5, emails_saved=3, applications_found=2)
    db.add(run)
    db.commit()

    resp = client.get(f"/api/v1/jobs/{run.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["emails_fetched"] == 5
    assert data["emails_saved"] == 3
    assert data["applications_found"] == 2


def test_get_job_status_404_for_missing(client):
    resp = client.get("/api/v1/jobs/9999")
    assert resp.status_code == 404


def test_get_job_status_404_for_non_integer_id(client):
    resp = client.get("/api/v1/jobs/not-a-number")
    assert resp.status_code == 404


def test_trigger_job_409_when_already_running(client, db):
    run = WorkerRun(status="running")
    db.add(run)
    db.commit()

    with patch("app.api.v1.jobs._run_worker") as mock_run:
        resp = client.post("/api/v1/jobs/email-check")

    mock_run.assert_not_called()
    assert resp.status_code == 409
