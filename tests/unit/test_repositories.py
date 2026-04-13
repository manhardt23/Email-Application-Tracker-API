"""
Unit tests for DB repositories using SQLite in-memory.

Covers: EmailRepository, AnalysisRepository, ApplicationRepository,
        CompanyRepository, WorkerRunRepository.
Uses the shared conftest fixtures (db, fresh_db).
"""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Company, WorkerRun
from app.db.repositories.analysis_repo import AnalysisRepository
from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository
from app.db.repositories.email_repo import EmailRepository
from app.db.repositories.worker_run_repo import WorkerRunRepository
from app.llm.base import EmailClassification

# ---------------------------------------------------------------------------
# Isolated engine for this module (independent of conftest)
# ---------------------------------------------------------------------------

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def _fresh():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def session():
    s = _Session()
    yield s
    s.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_email(session, message_id="<m1@test>", uid="uid-1"):
    repo = EmailRepository(session)
    email = repo.create(
        message_id=message_id,
        uid=uid,
        sender="hr@example.com",
        subject="Your application",
        body="body",
        received_date=datetime(2024, 1, 1),
    )
    session.commit()
    return email


# ---------------------------------------------------------------------------
# EmailRepository
# ---------------------------------------------------------------------------


class TestEmailRepository:
    def test_create_and_get_all(self, session):
        _create_email(session)
        repo = EmailRepository(session)
        all_emails = repo.get_all()
        assert len(all_emails) == 1
        assert all_emails[0].message_id == "<m1@test>"

    def test_find_by_message_id(self, session):
        _create_email(session)
        repo = EmailRepository(session)
        found = repo.find_by_message_id("<m1@test>")
        assert found is not None
        assert found.uid == "uid-1"

    def test_find_by_message_id_returns_none_for_missing(self, session):
        repo = EmailRepository(session)
        assert repo.find_by_message_id("<nope@test>") is None

    def test_find_by_uid(self, session):
        _create_email(session)
        repo = EmailRepository(session)
        found = repo.find_by_uid("uid-1")
        assert found is not None

    def test_find_by_uid_returns_none_for_missing(self, session):
        repo = EmailRepository(session)
        assert repo.find_by_uid("missing-uid") is None

    def test_exists_true_by_message_id(self, session):
        _create_email(session)
        repo = EmailRepository(session)
        assert repo.exists("<m1@test>", "some-other-uid") is True

    def test_exists_true_by_uid(self, session):
        _create_email(session)
        repo = EmailRepository(session)
        assert repo.exists(None, "uid-1") is True

    def test_exists_false_for_missing(self, session):
        repo = EmailRepository(session)
        assert repo.exists("<nope@test>", "nope-uid") is False

    def test_get_all_ordered_by_date_desc(self, session):
        repo = EmailRepository(session)
        repo.create(
            message_id="<old@test>", uid="uid-old",
            sender="s@e.com", subject="Old", body="b",
            received_date=datetime(2023, 1, 1),
        )
        repo.create(
            message_id="<new@test>", uid="uid-new",
            sender="s@e.com", subject="New", body="b",
            received_date=datetime(2024, 6, 1),
        )
        session.commit()
        all_emails = repo.get_all()
        assert all_emails[0].message_id == "<new@test>"
        assert all_emails[1].message_id == "<old@test>"


# ---------------------------------------------------------------------------
# AnalysisRepository
# ---------------------------------------------------------------------------


class TestAnalysisRepository:
    def test_create_sets_needs_review_false_for_high(self, session):
        email = _create_email(session)
        repo = AnalysisRepository(session)
        classification = EmailClassification(
            is_application=True, company="Acme", position="SWE",
            stage="applied", confidence="high",
        )
        analysis = repo.create(email.id, classification, model_used="test-model")
        session.commit()
        assert analysis.needs_review is False
        assert analysis.is_application is True

    def test_create_sets_needs_review_false_for_medium(self, session):
        email = _create_email(session)
        repo = AnalysisRepository(session)
        classification = EmailClassification(is_application=True, confidence="medium")
        analysis = repo.create(email.id, classification, model_used="test-model")
        session.commit()
        assert analysis.needs_review is False

    def test_create_sets_needs_review_true_for_low(self, session):
        email = _create_email(session)
        repo = AnalysisRepository(session)
        classification = EmailClassification(is_application=False, confidence="low")
        analysis = repo.create(email.id, classification, model_used="test-model")
        session.commit()
        assert analysis.needs_review is True

    def test_get_needs_review_returns_only_flagged(self, session):
        email1 = _create_email(session, message_id="<m2@test>", uid="uid-2")
        email2 = _create_email(session, message_id="<m3@test>", uid="uid-3")
        repo = AnalysisRepository(session)
        repo.create(
            email1.id, EmailClassification(is_application=True, confidence="high"), model_used="m"
        )
        repo.create(
            email2.id, EmailClassification(is_application=False, confidence="low"), model_used="m"
        )
        session.commit()
        needs_review = repo.get_needs_review()
        assert len(needs_review) == 1
        assert needs_review[0].needs_review is True

    def test_link_to_application(self, session):
        email = _create_email(session)
        repo = AnalysisRepository(session)
        analysis = repo.create(
            email.id, EmailClassification(is_application=True, confidence="high"), model_used="m"
        )
        session.commit()
        repo.link_to_application(analysis, 42)
        assert analysis.application_id == 42

    def test_get_by_worker_run(self, session):
        run = WorkerRun(status="completed")
        session.add(run)
        session.flush()
        email = _create_email(session)
        repo = AnalysisRepository(session)
        repo.create(
            email.id,
            EmailClassification(is_application=True, confidence="high"),
            model_used="m",
            worker_run_id=run.id,
        )
        session.commit()
        results = repo.get_by_worker_run(run.id)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# ApplicationRepository
# ---------------------------------------------------------------------------


class TestApplicationRepository:
    def test_find_or_create_creates_new(self, session):
        company = Company(name="Acme")
        session.add(company)
        session.flush()
        repo = ApplicationRepository(session)
        app = repo.find_or_create(company.id, "Engineer")
        session.commit()
        assert app.stage == "applied"
        assert app.position == "Engineer"

    def test_find_or_create_returns_existing(self, session):
        company = Company(name="Acme")
        session.add(company)
        session.flush()
        repo = ApplicationRepository(session)
        app1 = repo.find_or_create(company.id, "Engineer")
        session.commit()
        app2 = repo.find_or_create(company.id, "engineer")  # case-insensitive
        assert app1.id == app2.id

    def test_get_by_stage_filters(self, session):
        company = Company(name="Beta")
        session.add(company)
        session.flush()
        repo = ApplicationRepository(session)
        repo.find_or_create(company.id, "Dev")
        session.commit()
        results = repo.get_by_stage("applied")
        assert len(results) == 1
        assert repo.get_by_stage("offer") == []

    def test_get_all(self, session):
        company = Company(name="Corp")
        session.add(company)
        session.flush()
        repo = ApplicationRepository(session)
        repo.find_or_create(company.id, "Dev")
        repo.find_or_create(company.id, "QA")
        session.commit()
        assert len(repo.get_all()) == 2

    def test_get_by_id_returns_none_for_missing(self, session):
        repo = ApplicationRepository(session)
        assert repo.get_by_id(9999) is None

    def test_update_stage_advances_when_newer(self, session):
        company = Company(name="NewCo")
        session.add(company)
        session.flush()
        repo = ApplicationRepository(session)
        application = repo.find_or_create(company.id, "Analyst")
        session.commit()
        newer_date = datetime.now(UTC) + timedelta(days=1)
        repo.update_stage(application, "interview", newer_date)
        assert application.stage == "interview"

    def test_update_stage_does_not_revert_to_older(self, session):
        company = Company(name="OldCo")
        session.add(company)
        session.flush()
        repo = ApplicationRepository(session)
        application = repo.find_or_create(company.id, "Analyst")
        application.stage = "interview"
        application.last_updated = datetime(2025, 6, 1)
        session.commit()
        older_date = datetime(2024, 1, 1)
        repo.update_stage(application, "applied", older_date)
        assert application.stage == "interview"

    def test_update_stage_skips_when_no_stage(self, session):
        company = Company(name="SkipCo")
        session.add(company)
        session.flush()
        repo = ApplicationRepository(session)
        application = repo.find_or_create(company.id, "Dev")
        session.commit()
        repo.update_stage(application, None, datetime.now(UTC))
        assert application.stage == "applied"


# ---------------------------------------------------------------------------
# CompanyRepository
# ---------------------------------------------------------------------------


class TestCompanyRepository:
    def test_find_or_create_creates_new(self, session):
        repo = CompanyRepository(session)
        company = repo.find_or_create("Acme")
        session.commit()
        assert company.name == "Acme"

    def test_find_or_create_returns_existing_case_insensitive(self, session):
        repo = CompanyRepository(session)
        c1 = repo.find_or_create("Acme")
        session.commit()
        c2 = repo.find_or_create("ACME")
        assert c1.id == c2.id

    def test_find_by_name_returns_none_for_missing(self, session):
        repo = CompanyRepository(session)
        assert repo.find_by_name("Unknown Corp") is None


# ---------------------------------------------------------------------------
# WorkerRunRepository
# ---------------------------------------------------------------------------


class TestWorkerRunRepository:
    def test_try_create_queued_run(self, session):
        repo = WorkerRunRepository(session)
        run = repo.try_create_queued_run()
        session.commit()
        assert run is not None
        assert run.status == "queued"

    def test_claim_if_queued_transitions_to_running(self, session):
        # Insert directly to avoid try_create_queued_run's uniqueness guard
        run = WorkerRun(status="queued")
        session.add(run)
        session.commit()
        run_id = run.id
        repo = WorkerRunRepository(session)
        claimed = repo.claim_if_queued(run_id)
        assert claimed is not None
        # expire the cached object so SQLAlchemy re-reads from DB
        session.expire(claimed)
        assert claimed.status == "running"

    def test_claim_if_queued_returns_none_when_already_running(self, session):
        run = WorkerRun(status="running")
        session.add(run)
        session.commit()
        repo = WorkerRunRepository(session)
        assert repo.claim_if_queued(run.id) is None

    def test_complete_sets_status_and_counts(self, session):
        run = WorkerRun(status="running")
        session.add(run)
        session.commit()
        repo = WorkerRunRepository(session)
        repo.complete(run, emails_fetched=5, applications_found=2, emails_saved=3)
        assert run.status == "completed"
        assert run.emails_fetched == 5
        assert run.applications_found == 2
        assert run.emails_saved == 3

    def test_fail_sets_status_and_message(self, session):
        run = WorkerRun(status="running")
        session.add(run)
        session.commit()
        repo = WorkerRunRepository(session)
        repo.fail(run, "something broke")
        assert run.status == "failed"
        assert run.error_message == "something broke"

    def test_get_by_id_returns_none_for_missing(self, session):
        repo = WorkerRunRepository(session)
        assert repo.get_by_id(9999) is None

    def test_get_recent_returns_ordered_runs(self, session):
        now = datetime.now(UTC)
        r1 = WorkerRun(status="completed", queued_at=now - timedelta(minutes=10))
        r2 = WorkerRun(status="completed", queued_at=now - timedelta(minutes=1))
        session.add(r1)
        session.add(r2)
        session.commit()
        repo = WorkerRunRepository(session)
        recent = repo.get_recent(limit=10)
        assert len(recent) == 2
        # r2 queued more recently — should appear first
        assert recent[0].id == r2.id

    def test_reconcile_stale_marks_old_queued_as_failed(self, session):
        old_run = WorkerRun(
            status="queued",
            queued_at=datetime.now(UTC) - timedelta(minutes=9999),
        )
        session.add(old_run)
        session.commit()
        repo = WorkerRunRepository(session)
        repo.reconcile_stale_worker_runs(max_age_minutes=1)
        assert old_run.status == "failed"
        assert old_run.error_message is not None
