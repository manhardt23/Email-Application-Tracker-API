"""Dashboard glance, trends, and role groups. Counts come from stored rows only."""

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.db.models import Application, Company, Email, EmailAnalysis
from app.services.dashboard_view import (
    ApplicationSnapshot,
    build_glance,
    build_series,
    status_label,
    to_date,
)
from app.services.role_groups import classify_position, group_positions

TODAY = date(2026, 11, 23)  # Monday


def _snapshot(
    row_id: int,
    stage: str,
    position: str,
    applied_on: date,
    updated_on: date | None = None,
) -> ApplicationSnapshot:
    return ApplicationSnapshot(
        id=row_id,
        stage=stage,
        position=position,
        applied_on=applied_on,
        updated_on=updated_on if updated_on is not None else applied_on,
    )


def test_classify_position_uses_stored_title_and_first_group():
    cases = {
        "Help Desk Analyst": "help_desk",
        "Helpdesk": "help_desk",
        "Service Desk": "help_desk",
        "IT Support Help Desk": "help_desk",
        "IT Support Specialist": "it_support",
        "Desktop Support Technician": "it_support",
        "Technical Support": "it_support",
        "NOC Technician": "noc",
        "Network Operations Center": "noc",
        "Systems Administrator": "sysadmin",
        "Sysadmin": "sysadmin",
        "Linux Administrator": "sysadmin",
        "Network Engineer": "network",
        "Sr. Network Engineer": "network",
        "Software Engineer": "software",
        "SWE": "software",
        "SDE II": "software",
        "Full-Stack Developer": "software",
        "Frontend Engineer": "software",
        "DevOps Engineer": "other",
        "Data Analyst": "other",
        "Engineer": "other",
        "": "other",
    }
    for title, group_id in cases.items():
        assert classify_position(title) == group_id


def test_group_positions_keeps_stored_titles_and_does_not_add_rows():
    positions = [
        "Software Engineer",
        "software engineer",
        "Software Engineer",
        "Help Desk Analyst",
        "Data Analyst",
    ]
    groups = {group["id"]: group for group in group_positions(positions)}

    assert sum(group["applications"] for group in groups.values()) == len(positions)
    assert groups["software"]["applications"] == 3
    software_titles = {row["title"]: row["applications"] for row in groups["software"]["titles"]}
    assert software_titles == {"Software Engineer": 2, "software engineer": 1}
    assert groups["help_desk"]["applications"] == 1
    assert groups["other"]["titles"] == [{"title": "Data Analyst", "applications": 1}]
    assert groups["noc"]["applications"] == 0
    assert groups["noc"]["titles"] == []


def test_build_series_week_window_is_monday_buckets_inside_the_range():
    series = build_series(
        [TODAY, TODAY - timedelta(days=7), date(2026, 10, 1)],
        today=TODAY,
        days=30,
        granularity="week",
    )

    assert all(date.fromisoformat(point["day"]).weekday() == 0 for point in series)
    assert sum(point["applications"] for point in series) == 2
    counted = {point["day"]: point["applications"] for point in series}
    assert counted["2026-11-23"] == 1
    assert counted["2026-11-16"] == 1
    assert "2026-10-01" not in counted


def test_build_series_all_time_months_include_older_dates_and_zero_fill():
    series = build_series(
        [date(2024, 6, 15), date(2026, 11, 1)],
        today=TODAY,
        days=0,
        granularity="month",
    )

    assert series[0]["day"] == "2024-06-01"
    assert series[-1]["day"] == "2026-11-01"
    assert all(date.fromisoformat(point["day"]).day == 1 for point in series)
    assert sum(point["applications"] for point in series) == 2
    assert "2024" in series[0]["label"]
    assert series[0]["applications"] == 1


def test_build_series_empty_all_time_is_empty_and_window_still_zero_fills():
    assert build_series([], today=TODAY, days=0, granularity="month") == []
    daily = build_series([], today=TODAY, days=30, granularity="day")
    assert len(daily) == 30
    assert sum(point["applications"] for point in daily) == 0


def test_to_date_and_status_label_cover_stored_timestamp_shapes():
    eastern = timezone(timedelta(hours=-5))
    assert to_date(None) is None
    assert to_date("   ") is None
    assert to_date("not-a-date") is None
    assert to_date(date(2026, 3, 4)) == date(2026, 3, 4)
    assert to_date(datetime(2026, 1, 2, 15, 0)) == date(2026, 1, 2)
    assert to_date(datetime(2026, 1, 2, 22, 0, tzinfo=eastern)) == date(2026, 1, 3)
    assert to_date("2026-05-06") == date(2026, 5, 6)
    assert to_date("2026-05-06T23:30:00Z") == date(2026, 5, 6)
    assert to_date("2026-05-06 01:02:03") == date(2026, 5, 6)

    assert status_label("assessment") == "Interview"
    assert status_label("offer") == "Offer"
    assert status_label("rejected") == "Rejected"
    assert status_label("applied") == "Applied"
    assert status_label("nope") == "Applied"


def test_build_series_rejects_unknown_granularity_and_labels_weeks_across_years():
    with pytest.raises(ValueError):
        build_series([], today=TODAY, days=30, granularity="year")

    series = build_series(
        [date(2025, 12, 29), date(2026, 1, 5)],
        today=date(2026, 1, 10),
        days=30,
        granularity="week",
    )
    by_day = {point["day"]: point for point in series}
    assert by_day["2025-12-29"]["applications"] == 1
    assert "25" in by_day["2025-12-29"]["label"]
    assert by_day["2026-01-05"]["applications"] == 1
    assert sum(point["applications"] for point in series) == 2


def test_build_glance_uses_stored_dates_emails_and_stages():
    applications = [
        _snapshot(1, "applied", "Software Engineer", TODAY, TODAY),
        _snapshot(2, "assessment", "Help Desk", TODAY - timedelta(days=5), date(2026, 10, 1)),
        _snapshot(3, "rejected", "Data Analyst", date(2026, 10, 1), date(2026, 10, 1)),
        _snapshot(4, "mystery", "Recruiter", date(2026, 11, 1), date(2026, 11, 1)),
    ]
    # Application 2 was updated in October, but a linked email arrived last week.
    glance = build_glance(
        applications,
        {2: TODAY - timedelta(days=3)},
        today=TODAY,
        stale_days=14,
    )

    funnel = {row["name"]: row["value"] for row in glance["funnel"]}
    assert funnel == {"Applied": 1, "Interview": 1, "Offer": 0, "Rejected": 1}
    assert glance["other_stages"] == 1
    assert glance["total_applications"] == 4
    assert glance["responses_received"] == 2
    assert glance["response_rate"] == 50
    assert glance["this_week"] == 1
    assert glance["last_week"] == 1
    assert glance["last_applied_on"] == TODAY.isoformat()
    assert glance["days_since_last_application"] == 0
    assert glance["stale_days"] == 14
    # App 3 is quiet. App 2 is not, because the email is newer than the cutoff.
    # App 4 was updated Nov 1, which is more than 14 days before Nov 23.
    assert glance["stale_applications"] == 2


def _seed(db, *, company_name, position, stage="applied", applied_days_ago=0, updated_days_ago=0):
    company = db.query(Company).filter(Company.name == company_name).first()
    if company is None:
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


def _link_email(db, application, *, days_ago, uid):
    now = datetime.now(UTC)
    email = Email(
        uid=uid,
        sender="jobs@example.com",
        subject="Update",
        received_date=now - timedelta(days=days_ago),
    )
    db.add(email)
    db.flush()
    db.add(
        EmailAnalysis(
            email_id=email.id,
            application_id=application.id,
            is_application=True,
        )
    )
    db.commit()


def test_dashboard_glance_endpoint_counts_stored_rows(client, db):
    recent = _seed(db, company_name="A Corp", position="Software Engineer", applied_days_ago=0)
    quiet = _seed(
        db,
        company_name="B Corp",
        position="Data Analyst",
        stage="rejected",
        applied_days_ago=40,
        updated_days_ago=40,
    )
    revived = _seed(
        db,
        company_name="C Corp",
        position="Help Desk Analyst",
        stage="assessment",
        applied_days_ago=30,
        updated_days_ago=30,
    )
    _link_email(db, revived, days_ago=1, uid="1")
    _link_email(db, quiet, days_ago=40, uid="2")

    resp = client.get("/api/v1/dashboard/glance")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_applications"] == 3
    assert payload["stale_days"] == 14
    assert payload["stale_applications"] == 1
    assert payload["this_week"] == 1
    assert payload["days_since_last_application"] == 0
    assert payload["last_applied_on"] == to_date(recent.applied_date).isoformat()
    funnel = {row["name"]: row["value"] for row in payload["funnel"]}
    assert funnel["Applied"] == 1
    assert funnel["Interview"] == 1
    assert funnel["Rejected"] == 1


def test_dashboard_over_time_week_month_and_all_time(client, db):
    _seed(db, company_name="A Corp", position="Network Engineer", applied_days_ago=2)
    _seed(db, company_name="B Corp", position="NOC Analyst", applied_days_ago=10)
    _seed(db, company_name="C Corp", position="Systems Administrator", applied_days_ago=400)

    week = client.get("/api/v1/dashboard/applications-over-time?days=30&granularity=week")
    month = client.get("/api/v1/dashboard/applications-over-time?days=180&granularity=month")
    everything = client.get("/api/v1/dashboard/applications-over-time?days=0&granularity=month")
    invalid = client.get("/api/v1/dashboard/applications-over-time?granularity=year")

    assert week.status_code == 200
    week_rows = week.json()
    assert sum(row["applications"] for row in week_rows) == 2
    assert all(date.fromisoformat(row["day"]).weekday() == 0 for row in week_rows)

    assert month.status_code == 200
    assert sum(row["applications"] for row in month.json()) == 2
    assert all(date.fromisoformat(row["day"]).day == 1 for row in month.json())

    assert everything.status_code == 200
    assert sum(row["applications"] for row in everything.json()) == 3
    assert invalid.status_code == 422


def test_dashboard_role_breakdown_matches_stored_positions_only(client, db):
    _seed(db, company_name="A Corp", position="Software Engineer")
    _seed(db, company_name="B Corp", position="Software Engineer")
    _seed(db, company_name="C Corp", position="IT Support Specialist")
    _seed(db, company_name="D Corp", position="Office Manager")

    resp = client.get("/api/v1/dashboard/role-breakdown")

    assert resp.status_code == 200
    groups = {group["id"]: group for group in resp.json()["groups"]}
    assert sum(group["applications"] for group in groups.values()) == 4
    assert groups["software"]["applications"] == 2
    assert groups["software"]["titles"] == [{"title": "Software Engineer", "applications": 2}]
    assert groups["it_support"]["applications"] == 1
    assert groups["other"]["titles"] == [{"title": "Office Manager", "applications": 1}]
    assert set(groups) == {
        "help_desk",
        "it_support",
        "noc",
        "sysadmin",
        "network",
        "software",
        "other",
    }


def test_dashboard_glance_empty(client):
    resp = client.get("/api/v1/dashboard/glance")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_applications"] == 0
    assert payload["response_rate"] == 0
    assert payload["this_week"] == 0
    assert payload["last_week"] == 0
    assert payload["days_since_last_application"] is None
    assert payload["stale_applications"] == 0
    assert payload["last_applied_on"] is None
