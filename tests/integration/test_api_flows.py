"""
Integration tests — FastAPI app with SQLite in-memory DB.

Each test exercises a full request → repository → response path using the
shared conftest fixtures (client, db).  No mocking of DB or HTTP layers.

Marked ``integration`` so they can be run or skipped in isolation:
    pytest -m integration
    pytest -m "not integration"
"""
from datetime import datetime
from unittest.mock import patch

import pytest

from app.db.models import Application, Company, Email, EmailAnalysis

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_company_and_application(db, company_name="Integra Corp", stage="applied"):
    company = Company(name=company_name)
    db.add(company)
    db.flush()
    application = Application(company_id=company.id, position="Dev", stage=stage)
    db.add(application)
    db.commit()
    return application


def _seed_email_with_analysis(db, *, needs_review=False, message_id="msg-i1", uid="uid-i1"):
    email = Email(
        message_id=message_id,
        uid=uid,
        sender="hr@integra.com",
        subject="Application update",
        received_date=datetime(2024, 3, 1),
        body="Thank you for applying.",
    )
    db.add(email)
    db.flush()
    analysis = EmailAnalysis(
        email_id=email.id,
        is_application=True,
        detected_company="Integra Corp",
        detected_position="Dev",
        detected_stage="applied",
        confidence="high",
        needs_review=needs_review,
        model_used="test-model",
    )
    db.add(analysis)
    db.commit()
    return email


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_health_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Applications CRUD flow
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_application_lifecycle(client, db):
    """Seed → list → get → update → verify via GET."""
    app = _seed_company_and_application(db, stage="applied")

    # list
    list_resp = client.get("/api/v1/applications")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # get single
    get_resp = client.get(f"/api/v1/applications/{app.id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["stage"] == "applied"

    # update stage
    put_resp = client.put(f"/api/v1/applications/{app.id}", json={"stage": "interview"})
    assert put_resp.status_code == 200
    assert put_resp.json()["stage"] == "interview"

    # verify update persisted via a second GET
    verify_resp = client.get(f"/api/v1/applications/{app.id}")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["stage"] == "interview"


@pytest.mark.integration
def test_list_applications_stage_filter(client, db):
    _seed_company_and_application(db, company_name="A", stage="applied")
    _seed_company_and_application(db, company_name="B", stage="offer")

    resp = client.get("/api/v1/applications?stage=offer")
    assert resp.status_code == 200
    assert all(a["stage"] == "offer" for a in resp.json())


@pytest.mark.integration
def test_update_application_notes_clears(client, db):
    app = _seed_company_and_application(db)
    resp1 = client.put(f"/api/v1/applications/{app.id}", json={"notes": "initial"})
    assert resp1.status_code == 200
    assert resp1.json()["notes"] == "initial"
    resp = client.put(f"/api/v1/applications/{app.id}", json={"notes": None})
    assert resp.status_code == 200
    assert resp.json()["notes"] is None


# ---------------------------------------------------------------------------
# Emails flow
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_emails_list_and_review(client, db):
    _seed_email_with_analysis(db, needs_review=False, message_id="m1", uid="u1")
    _seed_email_with_analysis(db, needs_review=True, message_id="m2", uid="u2")

    list_resp = client.get("/api/v1/emails")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    review_resp = client.get("/api/v1/emails/review")
    assert review_resp.status_code == 200
    assert len(review_resp.json()) == 1
    assert review_resp.json()[0]["needs_review"] is True


@pytest.mark.integration
def test_emails_pagination(client, db):
    for i in range(5):
        _seed_email_with_analysis(db, message_id=f"m{i}", uid=f"u{i}")

    resp = client.get("/api/v1/emails?limit=2&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# Jobs flow
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_job_trigger_and_status_flow(client, db):
    """Trigger a job → verify queued status via GET."""
    with patch("app.api.v1.jobs._run_worker"):
        post_resp = client.post("/api/v1/jobs/email-check")

    assert post_resp.status_code == 202
    job_id = post_resp.json()["job_id"]

    get_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] in ("queued", "running", "completed")


@pytest.mark.integration
def test_job_409_on_duplicate_trigger(client, db):
    """Two concurrent trigger requests: second must return 409."""
    with patch("app.api.v1.jobs._run_worker"):
        first = client.post("/api/v1/jobs/email-check")
    assert first.status_code == 202

    with patch("app.api.v1.jobs._run_worker") as mock_run:
        second = client.post("/api/v1/jobs/email-check")
    mock_run.assert_not_called()
    assert second.status_code == 409


@pytest.mark.integration
def test_job_404_for_unknown_id(client):
    resp = client.get("/api/v1/jobs/99999")
    assert resp.status_code == 404
