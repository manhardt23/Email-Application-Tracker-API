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
from app.api.v1 import dashboard as dashboard_module
from app.api.v1 import emails as emails_module
from app.api.v1 import jobs as jobs_module
from app.api.v1.router import api_router
from app.auth import dependencies as auth_deps
from app.db.models import Application, Base, Company, Email, EmailAnalysis, User, WorkerRun
from app.services.worker_runtime import clear_max_emails_override, get_max_emails_override

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
    clear_max_emails_override()
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)
    clear_max_emails_override()


@pytest.fixture
def app():
    # Build a minimal FastAPI app — skip lifespan to avoid real DB creation.
    _admin = User(id=1, username="admin", password_hash="x", role="admin")
    _app = FastAPI()
    _app.include_router(api_router, prefix="/api/v1")
    _app.dependency_overrides[apps_module.get_db] = override_get_db
    _app.dependency_overrides[dashboard_module.get_db] = override_get_db
    _app.dependency_overrides[emails_module.get_db] = override_get_db
    _app.dependency_overrides[jobs_module.get_db] = override_get_db
    _app.dependency_overrides[auth_deps.get_db] = override_get_db
    _app.dependency_overrides[auth_deps.get_current_user] = lambda: _admin
    _app.dependency_overrides[auth_deps.require_admin] = lambda: _admin
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


def _seed_application(session, stage="applied", company_name="Acme Corp", position="Engineer"):
    company = Company(name=company_name)
    session.add(company)
    session.flush()
    application = Application(company_id=company.id, position=position, stage=stage)
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
    assert data["total"] == 1
    assert len(data["items"]) == 1
    row = data["items"][0]
    assert row["sender"] == "hr@example.com"
    assert row["is_application"] is True
    assert row["detected_company"] == "Acme"
    assert row["needs_review"] is False
    assert "application_id" in row


def test_list_emails_empty_returns_200(client):
    resp = client.get("/api/v1/emails")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_emails_empty_page_high_offset_returns_200(client, db):
    _seed_email_with_analysis(db)
    resp = client.get("/api/v1/emails?limit=10&offset=100")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 1


def test_list_emails_respects_limit(client, db):
    for i in range(3):
        _seed_email_with_analysis(db, message_id=f"msg-{i}", uid=f"uid-{i}")

    resp = client.get("/api/v1/emails?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3


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


def test_list_emails_review_empty_when_none_need_review(client, db):
    _seed_email_with_analysis(db, needs_review=False)

    resp = client.get("/api/v1/emails/review")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /emails/{id}/promote
# ---------------------------------------------------------------------------

def test_promote_email_creates_application_from_analysis(client, db):
    email = _seed_email_with_analysis(db, message_id="promote-1", uid="promote-u1")

    resp = client.post(f"/api/v1/emails/{email.id}/promote", json={})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["email_id"] == email.id
    assert payload["created"] is True
    assert payload["company_name"] == "Acme"
    assert payload["position"] == "Engineer"


def test_promote_email_creates_analysis_when_missing(client, db):
    email = Email(
        message_id="promote-2",
        uid="promote-u2",
        sender="hr@example.com",
        subject="Application update",
        received_date=datetime(2024, 2, 1),
        body="hello",
    )
    db.add(email)
    db.commit()
    db.refresh(email)

    resp = client.post(f"/api/v1/emails/{email.id}/promote", json={})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["created"] is True
    assert payload["company_name"] == "Unknown Company"
    assert payload["position"] == "Unknown Position"

    analysis = db.query(EmailAnalysis).filter(EmailAnalysis.email_id == email.id).first()
    assert analysis is not None
    assert analysis.application_id is not None
    assert analysis.is_application is True


def test_promote_email_is_idempotent_for_existing_target(client, db):
    email = _seed_email_with_analysis(db, message_id="promote-3", uid="promote-u3")

    first = client.post(f"/api/v1/emails/{email.id}/promote", json={})
    second = client.post(f"/api/v1/emails/{email.id}/promote", json={})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["application_id"] == second.json()["application_id"]
    assert second.json()["created"] is False


# ---------------------------------------------------------------------------
# POST /emails/{id}/dismiss
# ---------------------------------------------------------------------------

def test_dismiss_email_clears_needs_review(client, db):
    email = _seed_email_with_analysis(db, needs_review=True, message_id="d1", uid="d-u1")

    resp = client.post(f"/api/v1/emails/{email.id}/dismiss")

    assert resp.status_code == 200
    assert resp.json()["needs_review"] is False
    review = client.get("/api/v1/emails/review")
    assert review.json() == []


def test_dismiss_email_404_for_missing(client):
    resp = client.post("/api/v1/emails/9999/dismiss")
    assert resp.status_code == 404


def test_dismiss_email_404_when_no_analysis(client, db):
    email = Email(
        message_id="d2",
        uid="d-u2",
        sender="hr@example.com",
        subject="No analysis",
        received_date=datetime(2024, 1, 1),
        body="x",
    )
    db.add(email)
    db.commit()
    db.refresh(email)

    resp = client.post(f"/api/v1/emails/{email.id}/dismiss")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /applications/{id}/emails
# ---------------------------------------------------------------------------

def test_list_application_emails_returns_linked(client, db):
    email = _seed_email_with_analysis(db, message_id="link-1", uid="link-u1")
    promote = client.post(f"/api/v1/emails/{email.id}/promote", json={})
    app_id = promote.json()["application_id"]

    resp = client.get(f"/api/v1/applications/{app_id}/emails")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == email.id


def test_list_application_emails_404_for_missing_application(client):
    resp = client.get("/api/v1/applications/9999/emails")
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


def test_put_application_updates_company_and_position(client, db):
    application = _seed_application(db, company_name="Old Co", position="Old Role")

    resp = client.put(
        f"/api/v1/applications/{application.id}",
        json={"company_name": "New Co", "position": "New Role"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["company"]["name"] == "New Co"
    assert data["position"] == "New Role"


def test_put_application_conflict_on_existing_company_position(client, db):
    a1 = _seed_application(db, company_name="Acme", position="Engineer")
    _seed_application(db, company_name="Beta", position="Analyst")

    resp = client.put(
        f"/api/v1/applications/{a1.id}",
        json={"company_name": "Beta", "position": "Analyst"},
    )

    assert resp.status_code == 409


def test_put_application_rejects_blank_company_name(client, db):
    application = _seed_application(db)
    resp = client.put(f"/api/v1/applications/{application.id}", json={"company_name": "   "})
    assert resp.status_code == 422


def test_put_application_rejects_blank_position(client, db):
    application = _seed_application(db)
    resp = client.put(f"/api/v1/applications/{application.id}", json={"position": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /jobs/email-check and GET /jobs/{job_id}
# ---------------------------------------------------------------------------

def test_trigger_job_creates_worker_run(client):
    with patch("app.api.v1.jobs._run_worker") as mock_run:
        resp = client.post("/api/v1/jobs/email-check")

    assert resp.status_code == 202
    data = resp.json()
    mock_run.assert_called_once_with(int(data["job_id"]))
    assert "job_id" in data
    assert data["status"] == "queued"


def test_trigger_backfill_job_creates_worker_run_with_window(client):
    payload = {
        "from_date": "2026-01-01T00:00:00Z",
        "to_date": "2026-02-01T00:00:00Z",
        "max_emails": 50,
    }
    with patch("app.api.v1.jobs._run_worker") as mock_run:
        resp = client.post("/api/v1/jobs/email-backfill", json=payload)

    assert resp.status_code == 202
    data = resp.json()
    mock_run.assert_called_once()
    called = mock_run.call_args
    assert called.args[0] == int(data["job_id"])
    assert called.args[1].isoformat().startswith("2026-01-01T00:00:00")
    assert called.args[2].isoformat().startswith("2026-02-01T00:00:00")
    assert called.args[3] == 50


def test_trigger_backfill_job_422_for_invalid_date_range(client):
    payload = {
        "from_date": "2026-02-01T00:00:00Z",
        "to_date": "2026-01-01T00:00:00Z",
    }
    with patch("app.api.v1.jobs._run_worker") as mock_run:
        resp = client.post("/api/v1/jobs/email-backfill", json=payload)

    assert resp.status_code == 422
    mock_run.assert_not_called()


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


def test_list_jobs_returns_recent_runs(client, db):
    db.add_all(
        [
            WorkerRun(status="completed", emails_fetched=4, emails_saved=2, applications_found=1),
            WorkerRun(status="failed", error_message="boom"),
        ]
    )
    db.commit()

    resp = client.get("/api/v1/jobs")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert {row["status"] for row in data} == {"completed", "failed"}
    assert all("job_id" in row for row in data)


def test_list_jobs_empty_returns_empty_list(client):
    resp = client.get("/api/v1/jobs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_job_status_404_for_missing(client):
    resp = client.get("/api/v1/jobs/9999")
    assert resp.status_code == 404


def test_get_job_status_404_for_non_integer_id(client):
    resp = client.get("/api/v1/jobs/not-a-number")
    assert resp.status_code == 404


def test_trigger_job_409_when_already_queued(client, db):
    run = WorkerRun(status="queued")
    db.add(run)
    db.commit()

    with patch("app.api.v1.jobs._run_worker") as mock_run:
        resp = client.post("/api/v1/jobs/email-check")

    mock_run.assert_not_called()
    assert resp.status_code == 409


def test_trigger_backfill_job_409_when_already_queued(client, db):
    run = WorkerRun(status="queued")
    db.add(run)
    db.commit()

    with patch("app.api.v1.jobs._run_worker") as mock_run:
        resp = client.post(
            "/api/v1/jobs/email-backfill",
            json={"from_date": "2026-01-01T00:00:00Z"},
        )

    mock_run.assert_not_called()
    assert resp.status_code == 409


def test_trigger_job_409_when_already_running(client, db):
    run = WorkerRun(status="running")
    db.add(run)
    db.commit()

    with patch("app.api.v1.jobs._run_worker") as mock_run:
        resp = client.post("/api/v1/jobs/email-check")

    mock_run.assert_not_called()
    assert resp.status_code == 409


def test_set_worker_email_limit_sets_in_memory_override(client):
    resp = client.post("/api/v1/jobs/email-limit", json={"max_emails_per_run": 25})
    assert resp.status_code == 200
    assert resp.json() == {"max_emails_per_run": 25, "source": "in_memory_override"}
    assert get_max_emails_override() == 25


def test_set_worker_email_limit_rejects_out_of_range(client):
    resp = client.post("/api/v1/jobs/email-limit", json={"max_emails_per_run": 1001})
    assert resp.status_code == 422
