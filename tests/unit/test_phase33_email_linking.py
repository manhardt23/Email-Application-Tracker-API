"""
Phase 33 tests — link/unlink correspondence emails to an existing application.

Uses the shared ``client``/``db`` fixtures from ``tests/conftest.py`` (admin
auth bypassed via dependency overrides).
"""
from datetime import datetime

from app.db.models import Application, Company, Email, EmailAnalysis

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_email(session, *, with_analysis=True, message_id="link-msg-1", uid="link-uid-1"):
    email = Email(
        message_id=message_id,
        uid=uid,
        sender="recruiter@example.com",
        subject="Thanks for your time",
        received_date=datetime(2024, 3, 1),
        body="Thank you for chatting with us today.",
    )
    session.add(email)
    session.flush()
    if with_analysis:
        analysis = EmailAnalysis(
            email_id=email.id,
            is_application=False,
            detected_company=None,
            detected_position=None,
            detected_stage=None,
            confidence="low",
            needs_review=False,
            model_used="test-model",
        )
        session.add(analysis)
    session.commit()
    return email


def _seed_application(session, *, company_name="Acme Corp", position="Engineer", stage="applied"):
    company = Company(name=company_name)
    session.add(company)
    session.flush()
    application = Application(company_id=company.id, position=position, stage=stage)
    session.add(application)
    session.commit()
    return application


# ---------------------------------------------------------------------------
# POST /emails/{id}/link
# ---------------------------------------------------------------------------


def test_link_email_with_existing_analysis(client, db):
    email = _seed_email(db, message_id="link-1", uid="link-u1")
    application = _seed_application(db)

    resp = client.post(
        f"/api/v1/emails/{email.id}/link", json={"application_id": application.id}
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["application_id"] == application.id
    # Linking must not touch classification fields or force is_application.
    assert payload["is_application"] is False


def test_link_email_creates_manual_analysis_when_missing(client, db):
    email = _seed_email(db, with_analysis=False, message_id="link-2", uid="link-u2")
    application = _seed_application(db)

    resp = client.post(
        f"/api/v1/emails/{email.id}/link", json={"application_id": application.id}
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["application_id"] == application.id
    assert payload["needs_review"] is False

    analysis = db.query(EmailAnalysis).filter(EmailAnalysis.email_id == email.id).first()
    assert analysis is not None
    assert analysis.is_application is False
    assert analysis.application_id == application.id


def test_link_email_does_not_change_application_stage(client, db):
    email = _seed_email(db, message_id="link-3", uid="link-u3")
    application = _seed_application(db, stage="applied")

    resp = client.post(
        f"/api/v1/emails/{email.id}/link", json={"application_id": application.id}
    )

    assert resp.status_code == 200
    db.refresh(application)
    assert application.stage == "applied"


def test_link_email_idempotent_for_same_application(client, db):
    email = _seed_email(db, message_id="link-4", uid="link-u4")
    application = _seed_application(db)

    first = client.post(
        f"/api/v1/emails/{email.id}/link", json={"application_id": application.id}
    )
    second = client.post(
        f"/api/v1/emails/{email.id}/link", json={"application_id": application.id}
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["application_id"] == second.json()["application_id"]


def test_link_email_404_for_missing_email(client, db):
    application = _seed_application(db)
    resp = client.post(
        "/api/v1/emails/9999/link", json={"application_id": application.id}
    )
    assert resp.status_code == 404


def test_link_email_404_for_missing_application(client, db):
    email = _seed_email(db, message_id="link-5", uid="link-u5")
    resp = client.post(f"/api/v1/emails/{email.id}/link", json={"application_id": 9999})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /emails/{id}/unlink
# ---------------------------------------------------------------------------


def test_unlink_email_clears_application_id_only(client, db):
    email = _seed_email(db, message_id="unlink-1", uid="unlink-u1")
    application = _seed_application(db)
    client.post(f"/api/v1/emails/{email.id}/link", json={"application_id": application.id})

    resp = client.post(f"/api/v1/emails/{email.id}/unlink")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["application_id"] is None

    analysis = db.query(EmailAnalysis).filter(EmailAnalysis.email_id == email.id).first()
    assert analysis is not None
    assert analysis.application_id is None
    assert analysis.is_application is False


def test_unlink_email_404_for_missing_email(client):
    resp = client.post("/api/v1/emails/9999/unlink")
    assert resp.status_code == 404


def test_unlink_email_404_when_not_linked(client, db):
    email = _seed_email(db, message_id="unlink-2", uid="unlink-u2")
    resp = client.post(f"/api/v1/emails/{email.id}/unlink")
    assert resp.status_code == 404


def test_unlink_email_404_when_no_analysis(client, db):
    email = _seed_email(db, with_analysis=False, message_id="unlink-3", uid="unlink-u3")
    resp = client.post(f"/api/v1/emails/{email.id}/unlink")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /applications/{id}/emails reflects linked correspondence
# ---------------------------------------------------------------------------


def test_linked_email_appears_in_application_timeline(client, db):
    email = _seed_email(db, message_id="link-6", uid="link-u6")
    application = _seed_application(db)
    client.post(f"/api/v1/emails/{email.id}/link", json={"application_id": application.id})

    resp = client.get(f"/api/v1/applications/{application.id}/emails")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == email.id
