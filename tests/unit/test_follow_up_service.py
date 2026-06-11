from datetime import UTC, date, datetime, timedelta

from app.db.models import Application, Company, Email, EmailAnalysis
from app.services.follow_up_service import (
    FollowUpService,
    build_linkedin_search_url,
    build_suggested_message,
    collapse_company_name,
    days_since_contact,
)


def _seed_stalled_app(db, *, company_name="Acme", stage="applied", days_ago=20):
    company = Company(name=company_name)
    db.add(company)
    db.flush()
    applied = datetime.now(UTC) - timedelta(days=days_ago)
    app = Application(
        company_id=company.id,
        position="Engineer",
        stage=stage,
        applied_date=applied,
        last_updated=applied,
        last_contact_at=applied,
        follow_up_status="open",
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def test_collapse_company_name_strips_legal_suffix():
    assert collapse_company_name("Lockheed Martin Inc.") == "Lockheed Martin"


def test_build_linkedin_search_url_encodes_company():
    url = build_linkedin_search_url("IBM Corp")
    assert url.startswith("https://www.linkedin.com/search/results/people/?keywords=")
    assert "IBM" in url
    assert "recruiter" in url.lower()


def test_build_suggested_message_uses_contact_first_name():
    msg = build_suggested_message(
        contact_name="Jordan Lee",
        role="Backend Engineer",
        company="Viasat",
        applied_date=datetime.now(UTC) - timedelta(days=14),
    )
    assert msg.startswith("Hi Jordan,")
    assert "Backend Engineer" in msg
    assert "Viasat" in msg


def test_build_suggested_message_fallback_first_name():
    msg = build_suggested_message(
        contact_name=None,
        role="Engineer",
        company="Acme",
        applied_date=datetime.now(UTC) - timedelta(days=3),
    )
    assert msg.startswith("Hi there,")


def test_days_since_contact_uses_local_day_boundary():
    applied = datetime.now(UTC) - timedelta(days=10)
    assert days_since_contact(applied, applied) == 10


def test_follow_up_dashboard_stalled_and_upcoming(db):
    stale = _seed_stalled_app(db, company_name="Quiet Co", days_ago=25)
    upcoming_company = Company(name="Event Co")
    db.add(upcoming_company)
    db.flush()
    event_at = datetime.now(UTC) + timedelta(days=2)
    upcoming = Application(
        company_id=upcoming_company.id,
        position="PM",
        stage="interview",
        applied_date=datetime.now(UTC) - timedelta(days=5),
        last_updated=datetime.now(UTC),
        last_contact_at=datetime.now(UTC),
        next_event_at=event_at,
        follow_up_status="open",
    )
    db.add(upcoming)
    db.commit()

    payload = FollowUpService(db).get_dashboard(stale_after_days=14, limit=8)

    assert payload["counts"]["stalled"] >= 1
    assert payload["counts"]["upcoming"] >= 1
    stalled_ids = {item["application_id"] for item in payload["stalled"]}
    assert stale.id in stalled_ids
    assert any(item["application_id"] == upcoming.id for item in payload["upcoming"])
    stalled = next(item for item in payload["stalled"] if item["application_id"] == stale.id)
    assert stalled["urgency"] == "overdue"
    assert stalled["linkedin_search_url"]
    assert stalled["suggested_message"]


def test_terminal_stage_excluded_from_stalled(db):
    app = _seed_stalled_app(db, stage="no_response", days_ago=30)
    payload = FollowUpService(db).get_dashboard(stale_after_days=14, limit=8)
    assert app.id not in {item["application_id"] for item in payload["stalled"]}


def test_snoozed_application_hidden_until_date(db):
    app = _seed_stalled_app(db, days_ago=30)
    app.follow_up_status = "snoozed"
    app.snoozed_until = date.today() + timedelta(days=3)
    db.commit()

    payload = FollowUpService(db).get_dashboard(stale_after_days=14, limit=8)
    assert app.id not in {item["application_id"] for item in payload["stalled"]}


def test_recompute_last_contact_uses_latest_email(db):
    company = Company(name="Mail Co")
    db.add(company)
    db.flush()
    applied = datetime.now(UTC) - timedelta(days=30)
    app = Application(
        company_id=company.id,
        position="Dev",
        stage="applied",
        applied_date=applied,
        last_updated=applied,
    )
    db.add(app)
    db.flush()
    email = Email(
        uid="1",
        sender="hr@mail.co",
        subject="Thanks",
        received_date=datetime.now(UTC) - timedelta(days=2),
    )
    db.add(email)
    db.flush()
    db.add(
        EmailAnalysis(
            email_id=email.id,
            application_id=app.id,
            is_application=True,
            confidence="high",
            needs_review=False,
            model_used="test",
        )
    )
    db.commit()

    FollowUpService(db).recompute_last_contact_at(app)
    db.commit()
    db.refresh(app)

    assert app.last_contact_at is not None
    assert app.last_contact_at.date() == (datetime.now(UTC) - timedelta(days=2)).date()


def test_mark_followed_up_resets_clock(db):
    app = _seed_stalled_app(db, days_ago=30)
    before = app.last_contact_at
    FollowUpService(db).mark_followed_up(app, note="Reached out on LinkedIn")
    db.commit()
    db.refresh(app)
    assert app.last_contact_at > before
    assert app.follow_up_status == "open"
    assert "follow-up" in (app.notes or "")
