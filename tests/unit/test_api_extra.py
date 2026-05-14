"""
Additional API endpoint tests for paths not covered by test_phase5_api.py.

Covers: GET /health, GET /applications (list + stage filter + 404),
        GET /applications/{id}, GET /stats.
Uses shared conftest fixtures.
"""


from datetime import UTC, datetime, timedelta

from app.db.models import Application, Company, Email, EmailAnalysis, WorkerRun

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_application(db, stage="applied", company_name="Acme"):
    company = Company(name=company_name)
    db.add(company)
    db.flush()
    application = Application(company_id=company.id, position="Engineer", stage=stage)
    db.add(application)
    db.commit()
    return application


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health_returns_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /applications
# ---------------------------------------------------------------------------


def test_list_applications_returns_all(client, db):
    _seed_application(db, stage="applied", company_name="A Corp")
    _seed_application(db, stage="interview", company_name="B Corp")

    resp = client.get("/api/v1/applications")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_applications_empty_returns_404(client):
    resp = client.get("/api/v1/applications")
    assert resp.status_code == 404


def test_list_applications_filter_by_stage(client, db):
    _seed_application(db, stage="applied", company_name="A Corp")
    _seed_application(db, stage="offer", company_name="B Corp")

    resp = client.get("/api/v1/applications?stage=offer")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["stage"] == "offer"


def test_list_applications_filter_by_stage_not_found(client, db):
    _seed_application(db, stage="applied")

    resp = client.get("/api/v1/applications?stage=offer")

    assert resp.status_code == 404
    assert "offer" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /applications/{id}
# ---------------------------------------------------------------------------


def test_get_application_returns_correct_record(client, db):
    app = _seed_application(db)

    resp = client.get(f"/api/v1/applications/{app.id}")

    assert resp.status_code == 200
    assert resp.json()["stage"] == "applied"


def test_get_application_404_for_missing(client):
    resp = client.get("/api/v1/applications/9999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------


def test_stats_returns_zeroed_counts_when_empty(client):
    resp = client.get("/stats")
    assert resp.status_code == 200
    assert resp.json() == {
        "total_emails_processed": 0,
        "job_related_emails": 0,
        "worker_last_ran_at": None,
        "worker_run_count_7d": 0,
    }


def test_stats_returns_aggregates(client, db):
    now = datetime.now(UTC)

    email_1 = Email(
        message_id="m1",
        uid="1",
        sender="a@example.com",
        subject="Application received",
        received_date=now - timedelta(days=1),
        body="...",
    )
    email_2 = Email(
        message_id="m2",
        uid="2",
        sender="b@example.com",
        subject="Newsletter",
        received_date=now - timedelta(days=2),
        body="...",
    )
    db.add_all([email_1, email_2])
    db.flush()

    db.add_all(
        [
            EmailAnalysis(email_id=email_1.id, is_application=True, needs_review=False),
            EmailAnalysis(email_id=email_2.id, is_application=False, needs_review=True),
        ]
    )

    completed_recent = WorkerRun(
        status="completed",
        queued_at=now - timedelta(days=1),
        started_at=now - timedelta(days=1, minutes=5),
        finished_at=now - timedelta(days=1),
    )
    completed_old = WorkerRun(
        status="completed",
        queued_at=now - timedelta(days=10),
        started_at=now - timedelta(days=10, minutes=5),
        finished_at=now - timedelta(days=10),
    )
    running_recent = WorkerRun(
        status="running",
        queued_at=now - timedelta(hours=1),
        started_at=now - timedelta(hours=1),
        finished_at=None,
    )
    db.add_all([completed_recent, completed_old, running_recent])
    db.commit()

    resp = client.get("/stats")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_emails_processed"] == 2
    assert payload["job_related_emails"] == 1
    assert payload["worker_run_count_7d"] == 1
    assert payload["worker_last_ran_at"] is not None
