"""Behavior tests for deleting an application and applying a suggestion."""

from datetime import datetime

import pytest

from app.db.models import Application, Company, Email, EmailAnalysis, JobSuggestion


def _company(session, name):
    company = Company(name=name)
    session.add(company)
    session.flush()
    return company


def _application(session, company, position, stage="applied", notes=None):
    application = Application(
        company_id=company.id,
        position=position,
        stage=stage,
        notes=notes,
    )
    session.add(application)
    session.flush()
    return application


def _email(session, *, message_id, uid):
    email = Email(
        message_id=message_id,
        uid=uid,
        sender="hr@example.com",
        subject="Your application",
        received_date=datetime(2026, 3, 1),
        body="Thank you for applying.",
    )
    session.add(email)
    session.flush()
    return email


def _analysis(session, email, application):
    analysis = EmailAnalysis(
        email_id=email.id,
        is_application=True,
        detected_company="Acme",
        detected_position="Engineer",
        detected_stage="applied",
        confidence="high",
        needs_review=False,
        model_used="test-model",
        application_id=application.id,
    )
    session.add(analysis)
    session.flush()
    return analysis


def test_delete_leaves_emails_and_does_not_touch_another_application(client, db):
    db.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    acme = _company(db, "Acme")
    target = _application(db, acme, "Engineer")
    other_company = _company(db, "Other Co")
    other = _application(db, other_company, "Designer")
    target_email = _email(db, message_id="p44-del-target", uid="4430")
    other_email = _email(db, message_id="p44-del-other", uid="4431")
    _analysis(db, target_email, target)
    _analysis(db, other_email, other)
    db.commit()
    target_id = target.id
    other_id = other.id
    target_email_id = target_email.id
    other_email_id = other_email.id

    resp = client.delete(f"/api/v1/applications/{target_id}")

    assert resp.status_code == 204
    db.expire_all()
    assert db.get(Application, target_id) is None
    assert db.get(Email, target_email_id) is not None
    unlinked = db.query(EmailAnalysis).filter(EmailAnalysis.email_id == target_email_id).one()
    assert unlinked.application_id is None
    assert db.get(Application, other_id) is not None
    assert db.get(Email, other_email_id) is not None
    still_linked = db.query(EmailAnalysis).filter(EmailAnalysis.email_id == other_email_id).one()
    assert still_linked.application_id == other_id
    assert db.query(Email).count() == 2


def test_delete_application_with_no_emails(client, db):
    db.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    acme = _company(db, "Acme")
    empty = _application(db, acme, "Engineer")
    other_company = _company(db, "Other Co")
    other = _application(db, other_company, "Designer")
    kept = _email(db, message_id="p44-del-kept", uid="4432")
    _analysis(db, kept, other)
    db.commit()
    empty_id = empty.id
    other_id = other.id
    kept_id = kept.id

    resp = client.delete(f"/api/v1/applications/{empty_id}")

    assert resp.status_code == 204
    db.expire_all()
    assert db.get(Application, empty_id) is None
    assert db.get(Application, other_id) is not None
    assert db.get(Email, kept_id) is not None
    still_linked = db.query(EmailAnalysis).filter(EmailAnalysis.email_id == kept_id).one()
    assert still_linked.application_id == other_id
    assert db.query(Email).count() == 1


def test_second_delete_and_missing_application_are_404(client, db):
    company = _company(db, "Acme")
    application = _application(db, company, "Engineer")
    db.commit()
    application_id = application.id

    first = client.delete(f"/api/v1/applications/{application_id}")
    second = client.delete(f"/api/v1/applications/{application_id}")
    missing = client.delete("/api/v1/applications/999999")

    assert first.status_code == 204
    assert second.status_code == 404
    assert missing.status_code == 404
    db.expire_all()
    assert db.query(Application).count() == 0


def test_apply_creates_applied_application_and_leaves_other_suggestions(client, db):
    db.add(
        JobSuggestion(
            title="Data Analyst",
            company_name="Acme",
            pay="$140k",
            requirements_summary="SQL",
            apply_url="https://acme.example/jobs/42",
            dismissed=False,
        )
    )
    db.add(
        JobSuggestion(
            title="Designer",
            company_name="Other Co",
            pay=None,
            requirements_summary="",
            apply_url="https://other.example/design",
            dismissed=False,
        )
    )
    db.commit()

    suggestions = client.get("/api/v1/finder/suggestions").json()
    analyst = next(item for item in suggestions if item["title"] == "Data Analyst")
    applied = client.post(f"/api/v1/finder/suggestions/{analyst['id']}/apply")

    assert applied.status_code == 200
    body = applied.json()
    assert body["created"] is True
    assert body["company"] == "Acme"
    assert body["position"] == "Data Analyst"
    assert body["stage"] == "applied"

    remaining = client.get("/api/v1/finder/suggestions").json()
    assert [item["title"] for item in remaining] == ["Designer"]
    db.expire_all()
    stored = db.query(Application).one()
    assert stored.stage == "applied"
    assert stored.id == body["application_id"]
    notes = stored.notes or ""
    assert "https://acme.example/jobs/42" in notes
    assert "$140k" in notes
    rows = db.query(JobSuggestion).all()
    assert all(row.dismissed is False for row in rows)
    assert len(rows) == 2


def test_apply_existing_offer_keeps_stage_and_notes(client, db):
    company = _company(db, "Acme")
    application = _application(
        db,
        company,
        "Data Analyst",
        stage="offer",
        notes="Verbal offer on Monday",
    )
    suggestion = JobSuggestion(
        title="Data Analyst",
        company_name="Acme",
        pay="$140k",
        requirements_summary="SQL",
        apply_url="https://acme.example/jobs/42",
        dismissed=False,
    )
    db.add(suggestion)
    db.commit()
    application_id = application.id
    suggestion_id = suggestion.id

    applied = client.post(f"/api/v1/finder/suggestions/{suggestion_id}/apply")

    assert applied.status_code == 200
    assert applied.json() == {
        "application_id": application_id,
        "company": "Acme",
        "position": "Data Analyst",
        "stage": "offer",
        "created": False,
    }
    listed = client.get("/api/v1/finder/suggestions").json()
    assert all(item["id"] != suggestion_id for item in listed)
    db.expire_all()
    stored = db.get(Application, application_id)
    assert stored.stage == "offer"
    assert stored.notes == "Verbal offer on Monday"
    assert db.query(Application).count() == 1
    assert db.get(JobSuggestion, suggestion_id).dismissed is False


@pytest.mark.xfail(
    reason=(
        "Expected Acme Inc / data analyst to return the existing "
        "Acme, Inc. / Data Analyst application with created false. "
        "Apply returned created true and inserted another application."
    )
)
def test_apply_punctuation_variant_returns_the_existing_application(client, db):
    company = _company(db, "Acme, Inc.")
    application = _application(
        db,
        company,
        "Data Analyst",
        stage="offer",
        notes="Do not replace",
    )
    suggestion = JobSuggestion(
        title="data analyst",
        company_name="Acme Inc",
        pay="$90k",
        requirements_summary="SQL",
        apply_url="https://acme.example/analyst",
        dismissed=False,
    )
    db.add(suggestion)
    db.commit()
    application_id = application.id

    applied = client.post(f"/api/v1/finder/suggestions/{suggestion.id}/apply")

    assert applied.status_code == 200
    body = applied.json()
    assert body["created"] is False
    assert body["application_id"] == application_id
    assert body["stage"] == "offer"
    db.expire_all()
    assert db.query(Application).count() == 1
    assert db.query(Company).count() == 1
    stored = db.get(Application, application_id)
    assert stored.stage == "offer"
    assert stored.notes == "Do not replace"
    assert stored.company.name == "Acme, Inc."
    assert stored.position == "Data Analyst"
    assert db.query(JobSuggestion).one().dismissed is False
