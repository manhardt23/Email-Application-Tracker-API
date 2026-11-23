"""Phase 40 — no job-finder profile, and dismiss leaves a suggestion off the list."""

from types import SimpleNamespace

from app.db.database import Base
from app.db.models import Application, JobSuggestion
from app.llm.xai_finder import SuggestedJob
from app.services.job_finder import dismiss_suggestion


def _use_settings(monkeypatch, *, api_key: str | None):
    monkeypatch.setattr(
        "app.api.v1.finder.get_settings",
        lambda: SimpleNamespace(
            xai_api_key=api_key,
            xai_model="grok-3",
            xai_base_url="https://api.x.ai/v1",
        ),
    )


SUGGESTION_KEYS = {
    "id",
    "title",
    "company",
    "pay",
    "requirements_summary",
    "apply_url",
}


def test_profile_table_and_routes_are_gone(client):
    assert "qualification_profiles" not in Base.metadata.tables
    assert client.get("/api/v1/finder/profile").status_code == 404
    updated = client.put("/api/v1/finder/profile", json={"target_titles": "Engineer"})
    assert updated.status_code == 404


def test_suggestions_do_not_include_a_profile_fit(client, db):
    db.add(
        JobSuggestion(
            title="Backend Engineer",
            company_name="Acme",
            pay=None,
            requirements_summary="Python",
            apply_url="https://acme.example/apply",
        )
    )
    db.commit()

    listed = client.get("/api/v1/finder/suggestions").json()
    assert len(listed) == 1
    assert set(listed[0]) == SUGGESTION_KEYS
    assert listed[0]["title"] == "Backend Engineer"
    assert listed[0]["pay"] is None
    assert "qualification_fit" not in listed[0]
    assert "target_titles" not in listed[0]
    assert "skills" not in listed[0]


def test_dismiss_hides_suggestion_without_creating_an_application(client, db, monkeypatch):
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

    dismissed = client.post(f"/api/v1/finder/suggestions/{suggestion_id}/dismiss")
    assert dismissed.status_code == 200
    assert dismissed.json() == {"id": suggestion_id, "dismissed": True}
    assert client.get("/api/v1/finder/suggestions").json() == []

    db.expire_all()
    assert db.query(Application).count() == 0
    stored = db.query(JobSuggestion).one()
    assert stored.dismissed is True
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
    assert db.query(Application).count() == 0
    assert db.query(JobSuggestion).count() == 1


def test_dismiss_missing_suggestion_is_404(client, db):
    resp = client.post("/api/v1/finder/suggestions/9999/dismiss")
    assert resp.status_code == 404
    assert db.query(Application).count() == 0


def test_dismiss_is_idempotent(client, db):
    row = JobSuggestion(
        title="Writer",
        company_name="Acme",
        pay=None,
        requirements_summary="",
        apply_url="https://acme.example/write",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    first = dismiss_suggestion(db, row.id)
    second = dismiss_suggestion(db, row.id)
    assert first == second == {"id": row.id, "dismissed": True}
    assert client.get("/api/v1/finder/suggestions").json() == []
    assert db.query(Application).count() == 0
