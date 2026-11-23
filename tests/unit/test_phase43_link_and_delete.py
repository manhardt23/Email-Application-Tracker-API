"""Phase 43 — link incoming applications, and delete one without its emails.

Punctuation and spacing use the same normalize_label as the job finder.
Unknown company or title still creates or reuses the Unknown row.
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


def _seed_application(session, company, position, stage="applied"):
    application = Application(company_id=company.id, position=position, stage=stage)
    session.add(application)
    session.flush()
    return application


def _seed_email(session, *, company, position, message_id, uid, stage="applied"):
    email = Email(
        message_id=message_id,
        uid=uid,
        sender="hr@example.com",
        subject="Your application",
        received_date=datetime(2024, 1, 1),
        body="body text",
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


def test_promote_links_same_company_and_title_with_different_punctuation(client, db):
    other = _seed_company(db, "Other Co")
    _seed_application(db, other, "Sr. Software Engineer")
    company = _seed_company(db, "Acme, Inc.")
    application = _seed_application(db, company, "Sr. Software Engineer")
    db.commit()
    email = _seed_email(
        db,
        company="Acme Inc",
        position="Sr Software Engineer",
        message_id="p43-pair",
        uid="p43-pair",
    )

    resp = client.post(f"/api/v1/emails/{email.id}/promote", json={})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["created"] is False
    assert payload["application_id"] == application.id
    assert payload["company_name"] == "Acme, Inc."
    assert payload["position"] == "Sr. Software Engineer"
    db.expire_all()
    assert db.query(Application).count() == 2
    assert db.query(Company).count() == 2
    stored = db.get(Application, application.id)
    assert stored.company.name == "Acme, Inc."
    assert stored.position == "Sr. Software Engineer"


def test_promote_links_the_only_application_when_title_differs(client, db):
    company = _seed_company(db, "Acme, Inc.")
    application = _seed_application(db, company, "Software Engineer")
    db.commit()
    email = _seed_email(
        db,
        company="Acme Inc",
        position="Backend Engineer",
        message_id="p43-one",
        uid="p43-one",
    )

    resp = client.post(f"/api/v1/emails/{email.id}/promote", json={})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["created"] is False
    assert payload["application_id"] == application.id
    db.expire_all()
    assert db.query(Application).count() == 1
    stored = db.query(Application).one()
    assert stored.company.name == "Acme, Inc."
    assert stored.position == "Software Engineer"


def test_promote_creates_third_application_when_title_matches_none(client, db):
    company = _seed_company(db, "Acme, Inc.")
    _seed_application(db, company, "Software Engineer")
    _seed_application(db, company, "Data Scientist")
    db.commit()
    email = _seed_email(
        db,
        company="Acme Inc",
        position="Product Manager",
        message_id="p43-third",
        uid="p43-third",
    )

    resp = client.post(f"/api/v1/emails/{email.id}/promote", json={})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["created"] is True
    db.expire_all()
    assert db.query(Application).count() == 3
    assert db.query(Company).count() == 1
    created = db.get(Application, payload["application_id"])
    assert created.company_id == company.id
    assert created.position == "Product Manager"
    titles = {row.position for row in db.query(Application).all()}
    assert titles == {"Software Engineer", "Data Scientist", "Product Manager"}


def test_unknown_does_not_attach_to_a_real_company(client, db):
    company = _seed_company(db, "Acme")
    real = _seed_application(db, company, "Engineer")
    db.commit()
    email = _seed_email(
        db,
        company=UNKNOWN_COMPANY,
        position="Engineer",
        message_id="p43-unknown-co",
        uid="p43-unknown-co",
    )

    resp = client.post(f"/api/v1/emails/{email.id}/promote", json={})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["created"] is True
    assert payload["application_id"] != real.id
    assert payload["company_name"] == UNKNOWN_COMPANY
    db.expire_all()
    unknown = db.get(Application, payload["application_id"])
    assert unknown.company.name == UNKNOWN_COMPANY
    assert unknown.position == "Engineer"
    assert db.get(Application, real.id).company.name == "Acme"

    again = _seed_email(
        db,
        company=UNKNOWN_COMPANY,
        position="Engineer",
        message_id="p43-unknown-co-2",
        uid="p43-unknown-co-2",
    )
    reused = client.post(f"/api/v1/emails/{again.id}/promote", json={})
    assert reused.status_code == 200
    assert reused.json()["created"] is False
    assert reused.json()["application_id"] == unknown.id

    other = _seed_email(
        db,
        company="Acme",
        position=UNKNOWN_POSITION,
        message_id="p43-unknown-title",
        uid="p43-unknown-title",
    )
    title_resp = client.post(f"/api/v1/emails/{other.id}/promote", json={})
    assert title_resp.status_code == 200
    title_payload = title_resp.json()
    assert title_payload["created"] is True
    assert title_payload["application_id"] != real.id
    assert title_payload["position"] == UNKNOWN_POSITION
    assert title_payload["company_name"] == "Acme"
    db.expire_all()
    assert db.get(Application, real.id).position == "Engineer"


def test_delete_application_unlinks_emails_and_leaves_them(client, db):
    db.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    company = _seed_company(db, "Acme")
    application = _seed_application(db, company, "Engineer")
    other_company = _seed_company(db, "Other Co")
    other = _seed_application(db, other_company, "Designer")
    email = _seed_email(
        db,
        company="Acme",
        position="Engineer",
        message_id="p43-del",
        uid="p43-del",
    )
    kept = _seed_email(
        db,
        company="Other Co",
        position="Designer",
        message_id="p43-del-kept",
        uid="p43-del-kept",
    )
    email.analysis.application_id = application.id
    kept.analysis.application_id = other.id
    db.commit()
    email_id = email.id
    kept_id = kept.id
    application_id = application.id
    other_id = other.id

    resp = client.delete(f"/api/v1/applications/{application_id}")

    assert resp.status_code == 204
    db.expire_all()
    assert db.get(Application, application_id) is None
    assert db.get(Email, email_id) is not None
    unlinked = db.query(EmailAnalysis).filter(EmailAnalysis.email_id == email_id).one()
    assert unlinked.application_id is None
    assert db.get(Application, other_id) is not None
    still_linked = db.query(EmailAnalysis).filter(EmailAnalysis.email_id == kept_id).one()
    assert still_linked.application_id == other_id


def test_delete_application_404_for_missing(client):
    resp = client.delete("/api/v1/applications/9999")
    assert resp.status_code == 404


def test_worker_links_punctuation_variant_and_advances_stage(monkeypatch):
    import app.worker as worker_module

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    company = _seed_company(session, "Acme, Inc.")
    application = _seed_application(session, company, "Sr. Software Engineer")
    application.last_updated = datetime(2024, 1, 1)
    session.commit()
    application_id = application.id
    session.close()

    email = EmailData(
        message_id="<acme@example.test>",
        uid="43",
        sender="jobs@acme.test",
        subject="Interview",
        date=datetime(2026, 6, 1, tzinfo=UTC),
        body="Please interview",
    )
    email.is_application = True
    email.company = "Acme Inc"
    email.position = "Sr Software Engineer"
    email.stage = "interview"
    email.confidence = "high"

    class _Processor:
        def __init__(self, classifier):  # noqa: ANN001
            self.email_list = [email]
            self.application_emails = [email]

        def fetch_emails(self, limit, since_uid=1, from_date=None, to_date=None):  # noqa: ANN001
            return self.email_list

        def analyze_emails(self):
            return self.application_emails

        def get_high_confidence(self):
            return [email]

        def get_needs_review(self):
            return []

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
    monkeypatch.setattr(worker_module, "SessionLocal", Session)
    monkeypatch.setattr(worker_module.models.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(
        worker_module,
        "build_classifier",
        lambda settings: SimpleNamespace(model_name="test"),
    )
    monkeypatch.setattr(worker_module, "EmailProcessor", _Processor)
    monkeypatch.setattr(worker_module, "_resolve_uid_cursor", lambda last_uid, timeout: 0)

    assert worker_module.run() == 0

    check = Session()
    try:
        applications = check.query(Application).all()
        assert len(applications) == 1
        stored = applications[0]
        assert stored.id == application_id
        assert stored.position == "Sr. Software Engineer"
        assert stored.company.name == "Acme, Inc."
        assert stored.stage == "interview"
        assert check.query(Company).count() == 1
        analysis = check.query(EmailAnalysis).one()
        assert analysis.application_id == application_id
        assert check.query(Email).one().id == analysis.email_id
    finally:
        check.close()
