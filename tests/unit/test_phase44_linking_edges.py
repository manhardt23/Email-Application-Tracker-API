"""Behavior tests for linking an application email.

The worker and POST /emails/{id}/promote share one rule: same normalized
company and title links, a lone application at that company links when the
title differs, and unknown company or title never uses that company-only rule.
"""

from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Application, Base, Company, Email, EmailAnalysis
from app.services.application_matcher import UNKNOWN_COMPANY, UNKNOWN_POSITION
from app.services.email_service import EmailData


def _seed_company(session, name):
    company = Company(name=name)
    session.add(company)
    session.flush()
    return company


def _seed_application(session, company, position, stage="applied", last_updated=None):
    application = Application(company_id=company.id, position=position, stage=stage)
    if last_updated is not None:
        application.last_updated = last_updated
    session.add(application)
    session.flush()
    if last_updated is not None:
        application.last_updated = last_updated
    return application


def _seed_email(
    session,
    *,
    company,
    position,
    stage,
    message_id,
    uid,
    received,
    body,
):
    email = Email(
        message_id=message_id,
        uid=uid,
        sender="hr@example.com",
        subject="Your application",
        received_date=received,
        body=body,
    )
    session.add(email)
    session.flush()
    session.add(
        EmailAnalysis(
            email_id=email.id,
            is_application=True,
            detected_company=company,
            detected_position=position,
            detected_stage=stage,
            confidence="high",
            needs_review=False,
            model_used="test-model",
        )
    )
    session.commit()
    return email


def _promote(client, email):
    return client.post(f"/api/v1/emails/{email.id}/promote", json={})


def _application_email(*, message_id, uid, company, position, stage, when, body):
    email = EmailData(
        message_id=message_id,
        uid=uid,
        sender="hr@acme.test",
        subject="Update",
        date=when,
        body=body,
    )
    email.is_application = True
    email.company = company
    email.position = position
    email.stage = stage
    email.confidence = "high"
    return email


def _bind_worker(monkeypatch, session_factory):
    import app.worker as worker_module

    def _settings():
        return SimpleNamespace(
            llm_provider="ollama",
            groq_api_key=None,
            email_limit=10,
            max_emails_per_run=50,
            stale_run_ttl_minutes=1440,
            imap_timeout_seconds=30,
            safe_summary=lambda: "test",
        )

    monkeypatch.setattr(worker_module, "get_settings", _settings)
    monkeypatch.setattr(worker_module, "SessionLocal", session_factory)
    monkeypatch.setattr(worker_module.models.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(
        worker_module,
        "build_classifier",
        lambda settings: SimpleNamespace(model_name="test"),
    )
    monkeypatch.setattr(worker_module, "_resolve_uid_cursor", lambda last_uid, timeout: 0)
    return worker_module


def _run_worker(monkeypatch, worker_module, emails):
    class _Processor:
        def __init__(self, classifier):  # noqa: ANN001
            self.email_list = list(emails)
            self.application_emails = [item for item in emails if item.is_application]

        def fetch_emails(self, limit, since_uid=1, from_date=None, to_date=None):  # noqa: ANN001
            return self.email_list

        def analyze_emails(self):
            return self.application_emails

        def get_high_confidence(self):
            return [item for item in self.application_emails if item.confidence == "high"]

        def get_needs_review(self):
            return []

    monkeypatch.setattr(worker_module, "EmailProcessor", _Processor)
    return worker_module.run()


def _memory_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


def test_promote_links_case_and_punctuation_without_renaming(client, db):
    company = _seed_company(db, "Acme, Inc.")
    application = _seed_application(db, company, "Sr. Software Engineer")
    other = _seed_company(db, "Other Co")
    _seed_application(db, other, "Sr. Software Engineer")
    db.commit()
    email = _seed_email(
        db,
        company="ACME INC",
        position="sr software engineer",
        stage="interview",
        message_id="p44-case",
        uid="4401",
        received=datetime(2026, 6, 1),
        body="We would like to schedule an interview.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["created"] is False
    assert payload["application_id"] == application.id
    db.expire_all()
    assert db.query(Application).count() == 2
    assert db.query(Company).count() == 2
    stored = db.get(Application, application.id)
    assert stored.company.name == "Acme, Inc."
    assert stored.position == "Sr. Software Engineer"
    assert db.query(EmailAnalysis).one().application_id == application.id


def test_promote_punctuation_only_title_matches_one_of_two(client, db):
    company = _seed_company(db, "Acme")
    engineer = _seed_application(db, company, "Full-Stack Engineer")
    _seed_application(db, company, "Data Scientist")
    db.commit()
    email = _seed_email(
        db,
        company="Acme",
        position="Full Stack Engineer",
        stage="applied",
        message_id="p44-punct-title",
        uid="4402",
        received=datetime(2026, 6, 2),
        body="Thank you for applying. We received your application.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["created"] is False
    assert resp.json()["application_id"] == engineer.id
    db.expire_all()
    assert db.query(Application).count() == 2
    assert db.get(Application, engineer.id).position == "Full-Stack Engineer"


def test_promote_substring_title_does_not_steal_a_different_application(client, db):
    company = _seed_company(db, "Acme")
    short = _seed_application(db, company, "Engineer")
    senior = _seed_application(db, company, "Senior Engineer")
    db.commit()
    email = _seed_email(
        db,
        company="acme",
        position="Senior Engineer!",
        stage="interview",
        message_id="p44-substr",
        uid="4403",
        received=datetime(2026, 6, 3),
        body="We would like to schedule an interview.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["created"] is False
    assert resp.json()["application_id"] == senior.id
    assert resp.json()["application_id"] != short.id
    db.expire_all()
    assert db.query(Application).count() == 2
    assert db.get(Application, short.id).position == "Engineer"
    assert db.get(Application, senior.id).position == "Senior Engineer"


def test_promote_unmatched_title_with_two_applications_creates_a_new_one(client, db):
    company = _seed_company(db, "Acme")
    _seed_application(db, company, "Engineer")
    _seed_application(db, company, "Senior Engineer")
    db.commit()
    email = _seed_email(
        db,
        company="Acme",
        position="Staff Engineer",
        stage="applied",
        message_id="p44-third",
        uid="4404",
        received=datetime(2026, 6, 4),
        body="Thank you for applying. We received your application.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["created"] is True
    db.expire_all()
    assert db.query(Application).count() == 3
    created = db.get(Application, resp.json()["application_id"])
    assert created.company_id == company.id
    assert created.position == "Staff Engineer"
    titles = {row.position for row in db.query(Application).all()}
    assert titles == {"Engineer", "Senior Engineer", "Staff Engineer"}


def test_promote_different_title_links_the_only_application(client, db):
    company = _seed_company(db, "Acme, Inc.")
    only = _seed_application(db, company, "Senior Engineer")
    db.commit()
    email = _seed_email(
        db,
        company="acme inc",
        position="Engineer",
        stage="interview",
        message_id="p44-only",
        uid="4405",
        received=datetime(2026, 6, 5),
        body="We would like to schedule an interview.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["created"] is False
    assert resp.json()["application_id"] == only.id
    db.expire_all()
    assert db.query(Application).count() == 1
    stored = db.get(Application, only.id)
    assert stored.position == "Senior Engineer"
    assert stored.company.name == "Acme, Inc."


def test_promote_blank_company_and_title_do_not_use_the_company_only_rule(client, db):
    company = _seed_company(db, "Acme")
    only = _seed_application(db, company, "Engineer")
    db.commit()
    blank = _seed_email(
        db,
        company="   ",
        position="  ",
        stage="applied",
        message_id="p44-blank",
        uid="4406",
        received=datetime(2026, 6, 6),
        body="Thank you for applying. We received your application.",
    )

    first = _promote(client, blank)

    assert first.status_code == 200
    assert first.json()["created"] is True
    assert first.json()["application_id"] != only.id
    assert first.json()["company_name"] == UNKNOWN_COMPANY
    assert first.json()["position"] == UNKNOWN_POSITION
    db.expire_all()
    assert db.get(Application, only.id).position == "Engineer"
    assert db.get(Application, only.id).company.name == "Acme"

    again = _seed_email(
        db,
        company="",
        position="",
        stage="applied",
        message_id="p44-blank-2",
        uid="4407",
        received=datetime(2026, 6, 7),
        body="Thank you for applying. We received your application.",
    )
    second = _promote(client, again)
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["application_id"] == first.json()["application_id"]
    db.expire_all()
    assert db.query(Application).count() == 2


def test_promote_blank_title_does_not_attach_to_the_only_application(client, db):
    company = _seed_company(db, "Acme")
    only = _seed_application(db, company, "Engineer")
    other = _seed_application(db, company, "Designer")
    db.commit()
    email = _seed_email(
        db,
        company="Acme",
        position="   ",
        stage="applied",
        message_id="p44-blank-title",
        uid="4408",
        received=datetime(2026, 6, 8),
        body="Thank you for applying. We received your application.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["created"] is True
    assert resp.json()["application_id"] not in {only.id, other.id}
    assert resp.json()["position"] == UNKNOWN_POSITION
    assert resp.json()["company_name"] == "Acme"
    db.expire_all()
    assert db.get(Application, only.id).position == "Engineer"
    assert db.get(Application, other.id).position == "Designer"


def test_promote_unknown_company_does_not_use_the_company_only_rule(client, db):
    unknown = _seed_company(db, UNKNOWN_COMPANY)
    existing = _seed_application(db, unknown, "Engineer")
    db.commit()
    email = _seed_email(
        db,
        company=UNKNOWN_COMPANY,
        position="Designer",
        stage="applied",
        message_id="p44-unk",
        uid="4409",
        received=datetime(2026, 6, 9),
        body="Thank you for applying. We received your application.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["created"] is True
    assert resp.json()["application_id"] != existing.id
    assert resp.json()["company_name"] == UNKNOWN_COMPANY
    assert resp.json()["position"] == "Designer"
    db.expire_all()
    assert db.get(Application, existing.id).position == "Engineer"
    assert db.query(Application).count() == 2


def test_promote_company_names_do_not_match_as_substrings(client, db):
    labs = _seed_company(db, "Acme Labs")
    only = _seed_application(db, labs, "Engineer")
    db.commit()
    email = _seed_email(
        db,
        company="Acme",
        position="Engineer",
        stage="applied",
        message_id="p44-co-substr",
        uid="4410",
        received=datetime(2026, 6, 10),
        body="Thank you for applying. We received your application.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["created"] is True
    assert resp.json()["application_id"] != only.id
    assert resp.json()["company_name"] == "Acme"
    db.expire_all()
    assert db.get(Application, only.id).company.name == "Acme Labs"
    assert db.query(Company).count() == 2


def test_promote_newer_interview_advances_stage_without_renaming(client, db):
    company = _seed_company(db, "Acme, Inc.")
    application = _seed_application(
        db,
        company,
        "Sr. Software Engineer",
        stage="applied",
        last_updated=datetime(2026, 1, 1),
    )
    db.commit()
    email = _seed_email(
        db,
        company="acme inc",
        position="sr. software engineer",
        stage="interview",
        message_id="p44-advance",
        uid="4411",
        received=datetime(2026, 8, 1),
        body="We would like to schedule an interview.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["created"] is False
    assert resp.json()["application_id"] == application.id
    assert resp.json()["stage"] == "interview"
    db.expire_all()
    stored = db.get(Application, application.id)
    assert stored.stage == "interview"
    assert stored.company.name == "Acme, Inc."
    assert stored.position == "Sr. Software Engineer"


def test_promote_newer_applied_email_does_not_walk_interview_back(client, db):
    company = _seed_company(db, "Acme")
    application = _seed_application(
        db,
        company,
        "Engineer",
        stage="interview",
        last_updated=datetime(2026, 1, 1),
    )
    db.commit()
    email = _seed_email(
        db,
        company="Acme",
        position="Engineer",
        stage="applied",
        message_id="p44-no-back",
        uid="4412",
        received=datetime(2026, 9, 1),
        body="Thank you for applying. We received your application.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["application_id"] == application.id
    assert resp.json()["stage"] == "interview"
    db.expire_all()
    stored = db.get(Application, application.id)
    assert stored.stage == "interview"
    assert stored.position == "Engineer"


def test_promote_older_rejection_does_not_change_interview(client, db):
    company = _seed_company(db, "Acme")
    application = _seed_application(
        db,
        company,
        "Engineer",
        stage="interview",
        last_updated=datetime(2026, 8, 1),
    )
    db.commit()
    email = _seed_email(
        db,
        company="Acme",
        position="Engineer",
        stage="rejected",
        message_id="p44-older-rej",
        uid="4413",
        received=datetime(2026, 1, 1),
        body="We will not be moving forward with your application.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["application_id"] == application.id
    assert resp.json()["created"] is False
    db.expire_all()
    stored = db.get(Application, application.id)
    assert stored.stage == "interview"
    assert stored.position == "Engineer"
    assert stored.company.name == "Acme"


def test_promote_newer_rejection_is_stored_as_rejected(client, db):
    company = _seed_company(db, "Acme, Inc.")
    application = _seed_application(
        db,
        company,
        "Engineer",
        stage="applied",
        last_updated=datetime(2026, 1, 1),
    )
    db.commit()
    email = _seed_email(
        db,
        company="Acme Inc",
        position="Engineer",
        stage="rejected",
        message_id="p44-rej-upd",
        uid="4414",
        received=datetime(2026, 8, 1),
        body="We will not be moving forward with your application.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["created"] is False
    assert resp.json()["application_id"] == application.id
    assert resp.json()["stage"] == "rejected"
    db.expire_all()
    stored = db.get(Application, application.id)
    assert stored.stage == "rejected"
    assert stored.company.name == "Acme, Inc."
    assert stored.position == "Engineer"


def test_promote_new_rejection_is_not_stored_as_applied(client, db):
    email = _seed_email(
        db,
        company="Acme",
        position="Engineer",
        stage="rejected",
        message_id="p44-new-rej",
        uid="4415",
        received=datetime(2024, 5, 1),
        body="We will not be moving forward with your application.",
    )

    resp = _promote(client, email)

    assert resp.status_code == 200
    assert resp.json()["created"] is True
    assert resp.json()["stage"] == "rejected"
    assert resp.json()["company_name"] == "Acme"
    assert resp.json()["position"] == "Engineer"
    db.expire_all()
    stored = db.query(Application).one()
    assert stored.stage == "rejected"
    assert stored.position == "Engineer"


def test_promote_second_historical_email_advances_the_new_application(client, db):
    """Creating from an older email must not freeze the stage at wall-clock now."""
    first = _seed_email(
        db,
        company="Acme",
        position="Engineer",
        stage="applied",
        message_id="p44-clock-applied",
        uid="4416",
        received=datetime(2026, 1, 15, tzinfo=UTC),
        body="Thank you for applying. We received your application.",
    )
    second = _seed_email(
        db,
        company="Acme",
        position="Engineer",
        stage="interview",
        message_id="p44-clock-interview",
        uid="4417",
        received=datetime(2026, 2, 15, tzinfo=UTC),
        body="We would like to schedule an interview.",
    )

    created = _promote(client, first)
    advanced = _promote(client, second)

    assert created.status_code == 200
    assert created.json()["created"] is True
    assert created.json()["stage"] == "applied"
    assert advanced.status_code == 200
    assert advanced.json()["created"] is False
    assert advanced.json()["application_id"] == created.json()["application_id"]
    assert advanced.json()["stage"] == "interview"
    db.expire_all()
    assert db.query(Application).count() == 1
    assert db.query(Application).one().stage == "interview"


def test_promote_offer_after_interview_is_not_stuck_at_the_update_clock(client, db):
    company = _seed_company(db, "Acme")
    application = _seed_application(
        db,
        company,
        "Engineer",
        stage="applied",
        last_updated=datetime(2026, 1, 1),
    )
    db.commit()
    interview = _seed_email(
        db,
        company="Acme",
        position="Engineer",
        stage="interview",
        message_id="p44-clock-iv",
        uid="4418",
        received=datetime(2026, 8, 1, tzinfo=UTC),
        body="We would like to schedule an interview.",
    )
    offer = _seed_email(
        db,
        company="Acme",
        position="Engineer",
        stage="offer",
        message_id="p44-clock-offer",
        uid="4419",
        received=datetime(2026, 9, 1, tzinfo=UTC),
        body="We are pleased to extend an offer for the Engineer role.",
    )

    first = _promote(client, interview)
    second = _promote(client, offer)

    assert first.status_code == 200
    assert first.json()["stage"] == "interview"
    assert second.status_code == 200
    assert second.json()["application_id"] == application.id
    assert second.json()["stage"] == "offer"
    db.expire_all()
    assert db.get(Application, application.id).stage == "offer"


def test_promote_same_email_twice_does_not_insert_another_application(client, db):
    email = _seed_email(
        db,
        company="Acme, Inc.",
        position="Engineer",
        stage="applied",
        message_id="p44-twice",
        uid="4416",
        received=datetime(2026, 6, 1),
        body="Thank you for applying. We received your application.",
    )

    first = _promote(client, email)
    second = _promote(client, email)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert second.json()["application_id"] == first.json()["application_id"]
    db.expire_all()
    assert db.query(Application).count() == 1
    assert db.query(Email).count() == 1
    assert db.query(EmailAnalysis).one().application_id == first.json()["application_id"]


def test_worker_links_case_and_punctuation_without_renaming(monkeypatch):
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    session = Session()
    company = _seed_company(session, "Acme, Inc.")
    application = _seed_application(session, company, "Sr. Software Engineer")
    session.commit()
    application_id = application.id
    session.close()

    email = _application_email(
        message_id="<p44-worker-case@test>",
        uid="4420",
        company="ACME INC",
        position="sr software engineer",
        stage="interview",
        when=datetime(2026, 6, 1, tzinfo=UTC),
        body="We would like to schedule an interview.",
    )
    assert _run_worker(monkeypatch, worker_module, [email]) == 0

    check = Session()
    try:
        assert check.query(Application).count() == 1
        assert check.query(Company).count() == 1
        stored = check.get(Application, application_id)
        assert stored.company.name == "Acme, Inc."
        assert stored.position == "Sr. Software Engineer"
        assert check.query(EmailAnalysis).one().application_id == application_id
    finally:
        check.close()


def test_worker_substring_title_links_the_exact_application(monkeypatch):
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    session = Session()
    company = _seed_company(session, "Acme")
    short = _seed_application(session, company, "Engineer")
    senior = _seed_application(session, company, "Senior Engineer")
    session.commit()
    short_id = short.id
    senior_id = senior.id
    session.close()

    email = _application_email(
        message_id="<p44-worker-substr@test>",
        uid="4421",
        company="Acme",
        position="Senior-Engineer",
        stage="interview",
        when=datetime(2026, 6, 1, tzinfo=UTC),
        body="We would like to schedule an interview.",
    )
    assert _run_worker(monkeypatch, worker_module, [email]) == 0

    check = Session()
    try:
        assert check.query(Application).count() == 2
        assert check.query(EmailAnalysis).one().application_id == senior_id
        assert check.get(Application, short_id).position == "Engineer"
        assert check.get(Application, senior_id).position == "Senior Engineer"
    finally:
        check.close()


def test_worker_blank_company_and_title_do_not_attach_to_a_real_application(monkeypatch):
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    session = Session()
    company = _seed_company(session, "Acme")
    only = _seed_application(session, company, "Engineer")
    session.commit()
    only_id = only.id
    session.close()

    email = _application_email(
        message_id="<p44-worker-blank@test>",
        uid="4422",
        company="   ",
        position="  ",
        stage="applied",
        when=datetime(2026, 6, 1, tzinfo=UTC),
        body="Thank you for applying. We received your application.",
    )
    assert _run_worker(monkeypatch, worker_module, [email]) == 0

    check = Session()
    try:
        assert check.query(Application).count() == 2
        stored = check.get(Application, only_id)
        assert stored.company.name == "Acme"
        assert stored.position == "Engineer"
        linked = check.query(EmailAnalysis).one().application_id
        assert linked != only_id
        created = check.get(Application, linked)
        assert created.company.name == UNKNOWN_COMPANY
        assert created.position == UNKNOWN_POSITION
    finally:
        check.close()


def test_worker_does_not_walk_interview_back_to_applied(monkeypatch):
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    session = Session()
    company = _seed_company(session, "Acme, Inc.")
    application = _seed_application(
        session,
        company,
        "Engineer",
        stage="interview",
        last_updated=datetime(2026, 1, 1),
    )
    session.commit()
    application_id = application.id
    session.close()

    email = _application_email(
        message_id="<p44-worker-noback@test>",
        uid="4423",
        company="Acme Inc",
        position="Engineer",
        stage="applied",
        when=datetime(2026, 9, 1, tzinfo=UTC),
        body="Thank you for applying. We received your application.",
    )
    assert _run_worker(monkeypatch, worker_module, [email]) == 0

    check = Session()
    try:
        stored = check.get(Application, application_id)
        assert stored.stage == "interview"
        assert stored.company.name == "Acme, Inc."
        assert stored.position == "Engineer"
        assert check.query(Application).count() == 1
    finally:
        check.close()


def test_worker_older_email_does_not_change_stage(monkeypatch):
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    session = Session()
    company = _seed_company(session, "Acme")
    application = _seed_application(
        session,
        company,
        "Engineer",
        stage="interview",
        last_updated=datetime(2026, 8, 1),
    )
    session.commit()
    application_id = application.id
    session.close()

    email = _application_email(
        message_id="<p44-worker-older@test>",
        uid="4424",
        company="Acme",
        position="Engineer",
        stage="rejected",
        when=datetime(2024, 1, 1, tzinfo=UTC),
        body="We will not be moving forward with your application.",
    )
    assert _run_worker(monkeypatch, worker_module, [email]) == 0

    check = Session()
    try:
        stored = check.get(Application, application_id)
        assert stored.stage == "interview"
        assert stored.position == "Engineer"
    finally:
        check.close()


def test_worker_newer_rejection_is_stored_as_rejected(monkeypatch):
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    session = Session()
    company = _seed_company(session, "Acme, Inc.")
    application = _seed_application(
        session,
        company,
        "Engineer",
        stage="applied",
        last_updated=datetime(2026, 1, 1),
    )
    session.commit()
    application_id = application.id
    session.close()

    email = _application_email(
        message_id="<p44-worker-rej@test>",
        uid="4425",
        company="Acme Inc",
        position="Engineer",
        stage="rejected",
        when=datetime(2026, 8, 1, tzinfo=UTC),
        body="We will not be moving forward with your application.",
    )
    assert _run_worker(monkeypatch, worker_module, [email]) == 0

    check = Session()
    try:
        stored = check.get(Application, application_id)
        assert stored.stage == "rejected"
        assert stored.company.name == "Acme, Inc."
        assert stored.position == "Engineer"
        assert check.query(Application).count() == 1
    finally:
        check.close()


def test_worker_new_rejection_is_not_stored_as_applied(monkeypatch):
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    email = _application_email(
        message_id="<p44-worker-newrej@test>",
        uid="4426",
        company="Acme",
        position="Engineer",
        stage="rejected",
        when=datetime(2024, 5, 1, tzinfo=UTC),
        body="We will not be moving forward with your application.",
    )
    assert _run_worker(monkeypatch, worker_module, [email]) == 0

    check = Session()
    try:
        assert check.query(Application).count() == 1
        stored = check.query(Application).one()
        assert stored.stage == "rejected"
        assert stored.position == "Engineer"
        assert stored.company.name == "Acme"
    finally:
        check.close()


def test_worker_later_email_in_the_same_run_advances_a_new_application(monkeypatch):
    """Oldest-first history (backfill) must not keep the first email's stage."""
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    applied = _application_email(
        message_id="<p44-clock-applied@test>",
        uid="4429",
        company="Acme",
        position="Engineer",
        stage="applied",
        when=datetime(2026, 1, 1, tzinfo=UTC),
        body="Thank you for applying. We received your application.",
    )
    interview = _application_email(
        message_id="<p44-clock-interview@test>",
        uid="4430",
        company="Acme",
        position="Engineer",
        stage="interview",
        when=datetime(2026, 2, 1, tzinfo=UTC),
        body="We would like to schedule an interview.",
    )
    offer = _application_email(
        message_id="<p44-clock-offer@test>",
        uid="4431",
        company="Acme",
        position="Engineer",
        stage="offer",
        when=datetime(2026, 3, 1, tzinfo=UTC),
        body="We are pleased to extend an offer for the Engineer role.",
    )

    assert _run_worker(monkeypatch, worker_module, [applied, interview, offer]) == 0

    check = Session()
    try:
        assert check.query(Application).count() == 1
        stored = check.query(Application).one()
        assert stored.stage == "offer"
        assert stored.position == "Engineer"
        assert stored.company.name == "Acme"
        assert check.query(Email).count() == 3
    finally:
        check.close()


def test_worker_newest_first_batch_keeps_an_earlier_interview(monkeypatch):
    """Incremental fetch is newest-first. An earlier interview must still land.

    Trigger: one check contains a March "application viewed" (applied) and a
    February interview for the same role. Processing March first used to set
    last_updated to March and then drop the interview. The interview email
    was saved, so the next run skipped it as a duplicate and the stage stayed
    applied.
    """
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    viewed = _application_email(
        message_id="<p44-order-viewed@test>",
        uid="4440",
        company="Acme",
        position="Engineer",
        stage="applied",
        when=datetime(2026, 3, 1, tzinfo=UTC),
        body="Your application was viewed.",
    )
    interview = _application_email(
        message_id="<p44-order-interview@test>",
        uid="4439",
        company="Acme",
        position="Engineer",
        stage="interview",
        when=datetime(2026, 2, 1, tzinfo=UTC),
        body="We would like to schedule an interview.",
    )

    assert _run_worker(monkeypatch, worker_module, [viewed, interview]) == 0

    check = Session()
    try:
        stored = check.query(Application).one()
        assert stored.stage == "interview"
        assert check.query(Email).count() == 2
    finally:
        check.close()


def test_worker_newest_first_batch_advances_an_existing_application(monkeypatch):
    """A later applied status in the same check must not freeze an interview."""
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    session = Session()
    company = _seed_company(session, "Acme")
    application = _seed_application(
        session,
        company,
        "Engineer",
        stage="applied",
        last_updated=datetime(2026, 1, 15),
    )
    session.commit()
    application_id = application.id
    session.close()

    viewed = _application_email(
        message_id="<p44-order-existing-viewed@test>",
        uid="4442",
        company="Acme",
        position="Engineer",
        stage="applied",
        when=datetime(2026, 3, 1, tzinfo=UTC),
        body="Your application status is under review.",
    )
    interview = _application_email(
        message_id="<p44-order-existing-interview@test>",
        uid="4441",
        company="Acme",
        position="Engineer",
        stage="interview",
        when=datetime(2026, 2, 1, tzinfo=UTC),
        body="Your interview is confirmed.",
    )

    assert _run_worker(monkeypatch, worker_module, [viewed, interview]) == 0

    check = Session()
    try:
        stored = check.get(Application, application_id)
        assert stored.stage == "interview"
        assert check.query(Application).count() == 1
    finally:
        check.close()


def test_worker_newest_first_batch_still_lets_a_later_rejection_win(monkeypatch):
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    rejection = _application_email(
        message_id="<p44-order-reject@test>",
        uid="4444",
        company="Acme",
        position="Engineer",
        stage="rejected",
        when=datetime(2026, 3, 1, tzinfo=UTC),
        body="We will not be moving forward with your application.",
    )
    interview = _application_email(
        message_id="<p44-order-reject-interview@test>",
        uid="4443",
        company="Acme",
        position="Engineer",
        stage="interview",
        when=datetime(2026, 2, 1, tzinfo=UTC),
        body="We would like to schedule an interview.",
    )

    assert _run_worker(monkeypatch, worker_module, [rejection, interview]) == 0

    check = Session()
    try:
        stored = check.query(Application).one()
        assert stored.stage == "rejected"
    finally:
        check.close()


def test_worker_later_applied_email_does_not_walk_a_new_interview_back(monkeypatch):
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    interview = _application_email(
        message_id="<p44-clock-keep-iv@test>",
        uid="4432",
        company="Acme",
        position="Engineer",
        stage="interview",
        when=datetime(2026, 1, 1, tzinfo=UTC),
        body="We would like to schedule an interview.",
    )
    applied = _application_email(
        message_id="<p44-clock-keep-applied@test>",
        uid="4433",
        company="Acme",
        position="Engineer",
        stage="applied",
        when=datetime(2026, 2, 1, tzinfo=UTC),
        body="Thank you for applying. We received your application.",
    )

    assert _run_worker(monkeypatch, worker_module, [interview, applied]) == 0

    check = Session()
    try:
        stored = check.query(Application).one()
        assert stored.stage == "interview"
    finally:
        check.close()


def test_worker_same_email_twice_does_not_insert(monkeypatch):
    Session = _memory_session()
    worker_module = _bind_worker(monkeypatch, Session)
    first = _application_email(
        message_id="<p44-dup@test>",
        uid="4427",
        company="Acme",
        position="Engineer",
        stage="applied",
        when=datetime(2026, 6, 1, tzinfo=UTC),
        body="Thank you for applying. We received your application.",
    )
    second = _application_email(
        message_id="<p44-dup@test>",
        uid="4428",
        company="Acme",
        position="Designer",
        stage="interview",
        when=datetime(2026, 7, 1, tzinfo=UTC),
        body="We would like to schedule an interview.",
    )

    assert _run_worker(monkeypatch, worker_module, [first]) == 0
    assert _run_worker(monkeypatch, worker_module, [first, second]) == 0

    check = Session()
    try:
        assert check.query(Email).count() == 1
        assert check.query(Application).count() == 1
        stored = check.query(Application).one()
        assert stored.position == "Engineer"
        assert stored.company.name == "Acme"
        assert check.query(EmailAnalysis).count() == 1
    finally:
        check.close()
