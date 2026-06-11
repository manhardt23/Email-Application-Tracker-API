"""
Additional API endpoint tests for paths not covered by test_phase5_api.py.

Covers: GET /health, GET /applications (list + stage filter + 404),
        GET /applications/{id}, GET /stats.
Uses shared conftest fixtures.
"""


from datetime import UTC, date, datetime, timedelta

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


def _seed_application_with_dates(
    db,
    *,
    stage="applied",
    company_name="Acme",
    position="Engineer",
    applied_days_ago=0,
    updated_days_ago=0,
):
    company = db.query(Company).filter(Company.name == company_name).first()
    if not company:
        company = Company(name=company_name)
        db.add(company)
        db.flush()
    now = datetime.now(UTC)
    application = Application(
        company_id=company.id,
        position=position,
        stage=stage,
        applied_date=now - timedelta(days=applied_days_ago),
        last_updated=now - timedelta(days=updated_days_ago),
    )
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
    data = resp.json()
    assert data["total"] == 2
    names = {item["company"]["name"] for item in data["items"]}
    assert names == {"A Corp", "B Corp"}


def test_list_applications_empty_returns_200_empty_envelope(client):
    resp = client.get("/api/v1/applications")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_applications_filter_by_stage(client, db):
    _seed_application(db, stage="applied", company_name="A Corp")
    _seed_application(db, stage="offer", company_name="B Corp")

    resp = client.get("/api/v1/applications?stage=offer")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["stage"] == "offer"


def test_list_applications_filter_by_stage_not_found(client, db):
    _seed_application(db, stage="applied")

    resp = client.get("/api/v1/applications?stage=offer")

    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_list_applications_search_by_company_or_position(client, db):
    _seed_application(db, stage="applied", company_name="Acme Robotics")
    _seed_application(db, stage="applied", company_name="Globex")

    resp = client.get("/api/v1/applications?q=acme")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["company"]["name"] == "Acme Robotics"


def test_list_applications_pagination_limits_items_not_total(client, db):
    for i in range(3):
        _seed_application(db, stage="applied", company_name=f"Corp {i}")

    resp = client.get("/api/v1/applications?limit=2&offset=0")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3


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


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/*
# ---------------------------------------------------------------------------


def test_dashboard_metrics_returns_expected_counts(client, db):
    _seed_application(db, stage="applied", company_name="A Corp")
    _seed_application(db, stage="assessment", company_name="B Corp")
    _seed_application(db, stage="offer", company_name="C Corp")
    _seed_application(db, stage="rejected", company_name="D Corp")

    resp = client.get("/api/v1/dashboard/metrics")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_applications"] == 4
    assert payload["responses_received"] == 3
    assert payload["interviews_scheduled"] == 1
    assert payload["response_rate"] == 75


def test_dashboard_applications_over_time_returns_last_30_days(client, db):
    _seed_application_with_dates(db, company_name="A Corp", applied_days_ago=2)
    _seed_application_with_dates(db, company_name="B Corp", applied_days_ago=2)
    _seed_application_with_dates(db, company_name="C Corp", applied_days_ago=10)

    resp = client.get("/api/v1/dashboard/applications-over-time")

    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 30
    assert all("applications" in row and "label" in row for row in payload)
    total_in_window = sum(row["applications"] for row in payload)
    assert total_in_window == 3


def test_dashboard_status_breakdown_maps_assessment_to_interview(client, db):
    _seed_application(db, stage="applied", company_name="A Corp")
    _seed_application(db, stage="assessment", company_name="B Corp")
    _seed_application(db, stage="interview", company_name="C Corp")
    _seed_application(db, stage="rejected", company_name="D Corp")

    resp = client.get("/api/v1/dashboard/status-breakdown")

    assert resp.status_code == 200
    payload = {row["name"]: row["value"] for row in resp.json()}
    assert payload["Applied"] == 1
    assert payload["Interview"] == 2
    assert payload["Offer"] == 0
    assert payload["Rejected"] == 1


def test_dashboard_recent_applications_returns_ordered_records(client, db):
    _seed_application_with_dates(
        db,
        stage="offer",
        company_name="A Corp",
        position="Backend Engineer",
        applied_days_ago=1,
        updated_days_ago=1,
    )
    _seed_application_with_dates(
        db,
        stage="applied",
        company_name="B Corp",
        position="Frontend Engineer",
        applied_days_ago=5,
        updated_days_ago=3,
    )

    resp = client.get("/api/v1/dashboard/recent-applications?limit=2")

    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 2
    assert payload[0]["company"] == "A Corp"
    assert payload[0]["status"] == "Offer"
    assert "date_applied" in payload[0]


def test_dashboard_top_companies_returns_ranked_counts(client, db):
    _seed_application(db, stage="applied", company_name="A Corp")
    _seed_application(db, stage="interview", company_name="B Corp")
    _seed_application_with_dates(
        db,
        stage="offer",
        company_name="B Corp",
        position="Platform Engineer",
    )

    resp = client.get("/api/v1/dashboard/top-companies?limit=2")

    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 2
    assert payload[0]["company"] == "B Corp"
    assert payload[0]["applications"] == 2


def test_dashboard_follow_ups_returns_contract(client, db):
    app = _seed_application_with_dates(
        db,
        stage="applied",
        company_name="Stale Corp",
        applied_days_ago=30,
        updated_days_ago=30,
    )
    app.last_contact_at = datetime.now(UTC) - timedelta(days=20)
    app.follow_up_status = "open"
    db.commit()

    resp = client.get("/api/v1/dashboard/follow-ups?stale_after_days=14&limit=5")

    assert resp.status_code == 200
    payload = resp.json()
    assert "generated_at" in payload
    assert payload["config"]["stale_after_days"] == 14
    assert "counts" in payload
    assert any(item["application_id"] == app.id for item in payload["stalled"])


def test_application_followed_up_and_snooze(client, db):
    app = _seed_application_with_dates(
        db,
        stage="applied",
        company_name="Follow Co",
        applied_days_ago=30,
        updated_days_ago=30,
    )
    app.last_contact_at = datetime.now(UTC) - timedelta(days=20)
    db.commit()

    followed = client.post(f"/api/v1/applications/{app.id}/followed-up", json={"note": "Pinged"})
    assert followed.status_code == 200
    assert followed.json()["follow_up_status"] == "open"
    assert "Pinged" in (followed.json().get("notes") or "")

    snooze = client.post(
        f"/api/v1/applications/{app.id}/snooze",
        json={"until": (date.today() + timedelta(days=7)).isoformat()},
    )
    assert snooze.status_code == 200
    assert snooze.json()["follow_up_status"] == "snoozed"


def test_application_put_accepts_follow_up_contact_fields(client, db):
    app = _seed_application(db, company_name="Contact Co")
    resp = client.put(
        f"/api/v1/applications/{app.id}",
        json={
            "contact_name": "Jordan Lee",
            "contact_title": "Recruiter",
            "contact_linkedin_url": "https://www.linkedin.com/in/example",
            "next_event_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["contact_name"] == "Jordan Lee"
    assert body["contact_title"] == "Recruiter"
    assert body["contact_linkedin_url"].endswith("/example")
    assert body["next_event_at"] is not None
