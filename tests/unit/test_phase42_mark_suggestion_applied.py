"""Phase 42 — add a suggestion to applications without dismissing it."""

from types import SimpleNamespace

from app.db.models import Application, Company, JobSuggestion
from app.llm.xai_finder import SuggestedJob


def _use_settings(monkeypatch, *, api_key: str | None):
    monkeypatch.setattr(
        "app.api.v1.finder.get_settings",
        lambda: SimpleNamespace(
            xai_api_key=api_key,
            xai_model="grok-3",
            xai_base_url="https://api.x.ai/v1",
        ),
    )


def test_apply_creates_application_and_hides_suggestion(client, db, monkeypatch):
    db.add(
        JobSuggestion(
            title="Data Analyst",
            company_name="Acme",
            pay="$90k",
            requirements_summary="SQL",
            apply_url="https://acme.example/analyst",
        )
    )
    db.commit()
    suggestion_id = client.get("/api/v1/finder/suggestions").json()[0]["id"]
    assert db.query(Application).count() == 0

    applied = client.post(f"/api/v1/finder/suggestions/{suggestion_id}/apply")
    assert applied.status_code == 200
    body = applied.json()
    assert body["created"] is True
    assert body["company"] == "Acme"
    assert body["position"] == "Data Analyst"
    assert body["stage"] == "applied"
    assert set(body) == {"application_id", "company", "position", "stage", "created"}

    assert client.get("/api/v1/finder/suggestions").json() == []

    db.expire_all()
    assert db.query(Application).count() == 1
    stored_app = db.query(Application).one()
    assert stored_app.id == body["application_id"]
    assert stored_app.stage == "applied"
    assert stored_app.applied_date is not None
    assert stored_app.notes == "https://acme.example/analyst\n$90k"
    stored = db.query(JobSuggestion).one()
    assert stored.dismissed is False
    assert stored.title == "Data Analyst"

    def _fake(**kwargs):
        return [
            SuggestedJob(
                title="Data Analyst",
                company="Acme",
                pay="$90k",
                requirements_summary="SQL",
                apply_url="https://acme.example/analyst",
            )
        ]

    monkeypatch.setattr("app.services.job_finder.fetch_job_suggestions", _fake)
    _use_settings(monkeypatch, api_key="test-key")
    searched = client.post("/api/v1/finder/search", json={"query": "analyst"})
    assert searched.status_code == 200
    assert searched.json() == {"added": [], "skipped_existing": 1}
    assert client.get("/api/v1/finder/suggestions").json() == []
    db.expire_all()
    assert db.query(Application).count() == 1
    assert db.query(JobSuggestion).one().dismissed is False


def test_apply_without_pay_notes_are_only_the_apply_url(client, db):
    db.add(
        JobSuggestion(
            title="Writer",
            company_name="Acme",
            pay=None,
            requirements_summary="",
            apply_url="https://acme.example/write",
        )
    )
    db.commit()
    suggestion_id = client.get("/api/v1/finder/suggestions").json()[0]["id"]

    applied = client.post(f"/api/v1/finder/suggestions/{suggestion_id}/apply")
    assert applied.status_code == 200
    assert applied.json()["created"] is True

    db.expire_all()
    assert db.query(Application).one().notes == "https://acme.example/write"


def test_apply_existing_application_keeps_stage_and_notes(client, db):
    company = Company(name="Acme")
    db.add(company)
    db.flush()
    application = Application(
        company_id=company.id,
        position="Data Analyst",
        stage="interview",
        notes="Recruiter screen on Tuesday",
    )
    db.add(application)
    db.add(
        JobSuggestion(
            title="Data Analyst",
            company_name="Acme",
            pay="$90k",
            requirements_summary="SQL",
            apply_url="https://acme.example/analyst",
        )
    )
    db.commit()
    db.refresh(application)
    suggestion_id = db.query(JobSuggestion).one().id

    first = client.post(f"/api/v1/finder/suggestions/{suggestion_id}/apply")
    assert first.status_code == 200
    assert first.json() == {
        "application_id": application.id,
        "company": "Acme",
        "position": "Data Analyst",
        "stage": "interview",
        "created": False,
    }

    second = client.post(f"/api/v1/finder/suggestions/{suggestion_id}/apply")
    assert second.status_code == 200
    assert second.json()["application_id"] == application.id
    assert second.json()["created"] is False
    assert second.json()["stage"] == "interview"

    db.expire_all()
    assert db.query(Application).count() == 1
    stored = db.query(Application).one()
    assert stored.stage == "interview"
    assert stored.notes == "Recruiter screen on Tuesday"
    assert db.query(JobSuggestion).one().dismissed is False


def test_apply_missing_suggestion_is_404(client, db):
    resp = client.post("/api/v1/finder/suggestions/9999/apply")
    assert resp.status_code == 404
    assert db.query(Application).count() == 0
    assert db.query(Company).count() == 0
