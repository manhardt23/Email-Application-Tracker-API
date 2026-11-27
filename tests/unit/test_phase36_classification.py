"""Phase 36 — application emails the old gate dropped, without accepting newsletters."""

from datetime import datetime

import pytest

from app.db.models import Application, Company, Email, EmailAnalysis
from app.email_client.quick_filter import quick_filter
from app.llm.base import EmailClassification
from app.llm.errors import LLMProviderError, LLMResponseError
from app.llm.groq_adapter import _PROMPT as GROQ_PROMPT
from app.llm.ollama_adapter import _PROMPT as OLLAMA_PROMPT
from app.services.email_service import EmailData, EmailProcessor

# Wording a person would count as an application. (sender, subject, body, stage)
REAL_APPLICATIONS = [
    (
        "hr@acme.com",
        "Thank you for your application",
        "Thank you for your application to Software Engineer at Acme. "
        "We have received your application.",
        "applied",
    ),
    (
        "careers@acme.com",
        "Thanks for applying",
        "Thanks for applying to the Backend Engineer role.",
        "applied",
    ),
    (
        "noreply@indeed.com",
        "Your application was sent",
        "Your application was sent to Acme.",
        "applied",
    ),
    (
        "jobs-noreply@linkedin.com",
        "You applied",
        "You applied to Software Engineer at Initech.",
        "applied",
    ),
    (
        "notifications@greenhouse.io",
        "Application received",
        "Thank you for applying to Acme.",
        "applied",
    ),
    (
        "no-reply@myworkday.com",
        "Application update",
        "We\u2019ve received your application for the Analyst role.",
        "applied",
    ),
    (
        "hr@clever.co",
        "Application",
        "Thank you for your application. We will be in touch.",
        "applied",
    ),
    (
        "talent@acme.com",
        "Update",
        "We regret to inform you that we will not be moving forward with your application.",
        "rejected",
    ),
    (
        "talent@acme.com",
        "Your interest in Acme",
        "Thank you for your interest in the Staff Engineer position. "
        "After careful review we have decided to pursue other candidates.",
        "rejected",
    ),
    (
        "talent@acme.com",
        "Role update",
        "Unfortunately you were not selected for the role.",
        "rejected",
    ),
    (
        "talent@acme.com",
        "Update",
        "We will not be moving forward.",
        "rejected",
    ),
    (
        "hr@acme.com",
        "Interview invitation",
        "Please pick a time.",
        "interview",
    ),
    (
        "hr@acme.com",
        "Next step",
        "We'd like to schedule a phone screen for the role you applied for.",
        "interview",
    ),
    (
        "hr@acme.com",
        "Your interview",
        "Confirming your interview on Thursday at 2pm.",
        "interview",
    ),
    (
        "hr@acme.com",
        "Offer",
        "We're pleased to extend an offer of employment for the Engineer role.",
        "offer",
    ),
    (
        "hr@acme.com",
        "Offer letter",
        "Your offer letter is attached.",
        "offer",
    ),
    (
        "hr@acme.com",
        "Coding challenge",
        "Please complete this coding challenge for your application.",
        "assessment",
    ),
    (
        "hr@acme.com",
        "Take-home",
        "Here is the take-home assignment for the role.",
        "assessment",
    ),
]

# Ordinary mail that must not become an application.
NOT_APPLICATIONS = [
    (
        "noreply@indeed.com",
        "New jobs for you",
        "Many new positions available near you.",
    ),
    (
        "jobs@board.com",
        "We're hiring engineers",
        "We have open positions for software engineers. Apply now.",
    ),
    (
        "news@example.com",
        "Newsletter",
        "Check out our latest updates this week.",
    ),
    (
        "deals@shop.com",
        "Limited time offer",
        "50% off this weekend only. Special offer for subscribers.",
    ),
    (
        "jobs-noreply@linkedin.com",
        "Jobs you might like",
        "Recommended jobs based on your profile.",
    ),
    (
        "jobs-noreply@linkedin.com",
        "More roles",
        "Based on your application to Acme, here are similar positions you might like.",
    ),
    (
        "news@example.com",
        "Interview with our CEO",
        "Our founder sat down to talk about the product roadmap.",
    ),
    (
        "billing@example.com",
        "Membership",
        "Resume your membership to keep reading.",
    ),
    (
        "alerts@example.com",
        "Closed role",
        "This position has been filled. Similar jobs you might like are below.",
    ),
]


class TestQuickFilterRealApplications:
    def test_real_application_mail_reaches_the_classifier(self):
        for sender, subject, body, _stage in REAL_APPLICATIONS:
            assert quick_filter(sender, subject, body) is True, subject

    def test_newsletters_and_job_alerts_are_skipped(self):
        for sender, subject, body in NOT_APPLICATIONS:
            assert quick_filter(sender, subject, body) is False, subject

    def test_job_board_match_is_a_domain_suffix(self):
        # "lever.co" is not a substring match, so clever.co is an employer.
        assert quick_filter(
            "hr@clever.co",
            "Thanks",
            "Thank you for your application.",
        ) is True
        assert quick_filter(
            "alerts@jobs.lever.co",
            "New jobs for you",
            "Open positions. Apply now.",
        ) is False


class _ScriptedClassifier:
    def __init__(self, result: EmailClassification | None) -> None:
        self.result = result
        self.provider_name = "groq"
        self.calls = 0

    def classify_email(self, sender: str, subject: str, body: str) -> EmailClassification | None:
        self.calls += 1
        return self.result


class TestReconcileFalseNegatives:
    def test_model_no_does_not_drop_an_explicit_rejection(self):
        email = EmailData(
            message_id="<r@acme.com>",
            uid="1",
            sender="talent@acme.com",
            subject="Update",
            date=None,
            body=(
                "We regret to inform you that we will not be moving forward "
                "with your application."
            ),
        )
        classifier = _ScriptedClassifier(
            EmailClassification(is_application=False, stage=None, confidence="high")
        )

        assert email.classify(classifier) is True
        assert email.stage == "rejected"
        assert email.is_application is True
        assert classifier.calls == 1

    def test_model_no_does_not_drop_an_interview_or_offer(self):
        interview = EmailData(
            message_id="<i@acme.com>",
            uid="2",
            sender="hr@acme.com",
            subject="Interview invitation",
            date=None,
            body="Please pick a time.",
        )
        offer = EmailData(
            message_id="<o@acme.com>",
            uid="3",
            sender="hr@acme.com",
            subject="Offer letter",
            date=None,
            body="Your offer letter is attached.",
        )
        refused = EmailClassification(is_application=False, confidence="high")

        assert interview.classify(_ScriptedClassifier(refused)) is True
        assert interview.stage == "interview"
        assert offer.classify(_ScriptedClassifier(refused)) is True
        assert offer.stage == "offer"

    def test_rejection_wording_outranks_a_model_stage_of_applied(self):
        email = EmailData(
            message_id="<m@acme.com>",
            uid="4",
            sender="hr@acme.com",
            subject="Thank you for your application",
            date=None,
            body="Thank you for your application. We have decided to pursue other candidates.",
        )
        email.classify(
            _ScriptedClassifier(
                EmailClassification(
                    is_application=True,
                    company="Acme",
                    position="Engineer",
                    stage="applied",
                    confidence="high",
                )
            )
        )
        assert email.is_application is True
        assert email.stage == "rejected"
        assert email.company == "Acme"
        assert email.confidence == "high"

    def test_missing_model_result_still_keeps_an_explicit_application(self):
        email = EmailData(
            message_id="<none@acme.com>",
            uid="7",
            sender="hr@acme.com",
            subject="Thanks for applying",
            date=None,
            body="Thanks for applying to the Backend Engineer role.",
        )
        assert email.classify(_ScriptedClassifier(None)) is True
        assert email.stage == "applied"
        assert email.confidence == "medium"

    def test_unreadable_model_reply_does_not_abort_the_batch(self):
        """One bad JSON reply must not stop later messages in the same check."""

        class _FailsThenClassifies:
            provider_name = "groq"

            def __init__(self) -> None:
                self.calls = 0

            def classify_email(self, sender: str, subject: str, body: str):
                self.calls += 1
                if self.calls == 1:
                    raise LLMResponseError("No JSON object found in provider response.")
                return EmailClassification(
                    is_application=True,
                    company="Initech",
                    position="Analyst",
                    stage="applied",
                    confidence="high",
                )

        ambiguous = EmailData(
            message_id="<bad@acme.com>",
            uid="8",
            sender="recruiter@agency.com",
            subject="Candidate resume",
            date=None,
            body="Please send your resume if you want to be considered a candidate.",
        )
        clear = EmailData(
            message_id="<ok@acme.com>",
            uid="9",
            sender="hr@initech.com",
            subject="Thank you for your application",
            date=None,
            body="Thank you for your application to Analyst at Initech.",
        )
        processor = EmailProcessor(_FailsThenClassifies())
        processor.email_list = [ambiguous, clear]

        found = processor.analyze_emails()

        assert ambiguous.is_application is False
        assert found == [clear]
        assert clear.is_application is True
        assert clear.company == "Initech"

    def test_unreadable_model_reply_still_keeps_an_explicit_rejection(self):
        email = EmailData(
            message_id="<rej@acme.com>",
            uid="10",
            sender="talent@acme.com",
            subject="Update",
            date=None,
            body=(
                "We regret to inform you that we will not be moving forward "
                "with your application."
            ),
        )

        class _Unreadable:
            provider_name = "groq"

            def classify_email(self, sender: str, subject: str, body: str):
                raise LLMResponseError("Invalid JSON in provider response.")

        assert email.classify(_Unreadable()) is True
        assert email.stage == "rejected"
        assert email.is_application is True

    def test_provider_outage_still_aborts_classification(self):
        email = EmailData(
            message_id="<down@acme.com>",
            uid="11",
            sender="hr@acme.com",
            subject="Thank you for your application",
            date=None,
            body="Thank you for your application to Engineer at Acme.",
        )

        class _Down:
            provider_name = "groq"

            def classify_email(self, sender: str, subject: str, body: str):
                raise LLMProviderError("Groq classification failed.")

        processor = EmailProcessor(_Down())
        processor.email_list = [email]
        with pytest.raises(LLMProviderError):
            processor.analyze_emails()

    def test_ambiguous_mail_stays_not_an_application_when_the_model_says_no(self):
        email = EmailData(
            message_id="<c@acme.com>",
            uid="5",
            sender="recruiter@agency.com",
            subject="Candidate resume",
            date=None,
            body="Please send your resume if you want to be considered a candidate.",
        )
        assert quick_filter(email.sender, email.subject, email.body) is True
        assert email.classify(
            _ScriptedClassifier(EmailClassification(is_application=False, confidence="medium"))
        ) is False

    def test_newsletter_the_model_accepts_is_not_saved_as_an_application(self):
        processor = EmailProcessor(
            _ScriptedClassifier(
                EmailClassification(is_application=True, stage="applied", confidence="high")
            )
        )
        processor.email_list = [
            EmailData(
                message_id="<n@news.com>",
                uid="6",
                sender="jobs-noreply@linkedin.com",
                subject="Jobs you might like",
                date=None,
                body="Recommended jobs based on your profile. Apply now.",
            )
        ]

        assert processor.analyze_emails() == []
        assert processor.email_list[0].is_application is False

    def test_both_adapters_share_the_stricter_prompt(self):
        assert GROQ_PROMPT is OLLAMA_PROMPT
        rendered = GROQ_PROMPT.format(sender="a", subject="b", body="c")
        assert "not moving forward" in rendered
        assert "offer letter" in rendered
        assert "jobs you might like" in rendered
        assert "special offer" in rendered


def test_promote_rejection_is_not_stored_as_applied(client, db):
    email = Email(
        message_id="promote-reject",
        uid="promote-reject-1",
        sender="talent@acme.com",
        subject="Update",
        received_date=datetime(2024, 5, 1),
        body="We regret to inform you that we will not be moving forward with your application.",
    )
    db.add(email)
    db.commit()
    db.refresh(email)

    resp = client.post(f"/api/v1/emails/{email.id}/promote", json={"stage": "applied"})

    assert resp.status_code == 200
    assert resp.json()["stage"] == "rejected"
    analysis = db.query(EmailAnalysis).filter(EmailAnalysis.email_id == email.id).one()
    assert analysis.is_application is True
    assert analysis.detected_stage == "rejected"


def test_promote_explicit_stage_wins(client, db):
    email = Email(
        message_id="promote-explicit",
        uid="promote-explicit-1",
        sender="talent@acme.com",
        subject="Update",
        received_date=datetime(2024, 5, 2),
        body="We will not be moving forward with your application.",
    )
    db.add(email)
    db.commit()
    db.refresh(email)

    resp = client.post(f"/api/v1/emails/{email.id}/promote", json={"stage": "interview"})

    assert resp.status_code == 200
    assert resp.json()["stage"] == "interview"


def test_promote_does_not_downgrade_an_existing_interview(client, db):
    company = Company(name="Acme")
    db.add(company)
    db.flush()
    application = Application(company_id=company.id, position="Engineer", stage="interview")
    db.add(application)
    email = Email(
        message_id="promote-ack",
        uid="promote-ack-1",
        sender="hr@acme.com",
        subject="Thank you for applying",
        received_date=datetime(2024, 4, 1),
        body="Thank you for applying. We received your application.",
    )
    db.add(email)
    db.flush()
    db.add(
        EmailAnalysis(
            email_id=email.id,
            is_application=False,
            detected_company="Acme",
            detected_position="Engineer",
            detected_stage="applied",
            confidence="low",
            needs_review=True,
            model_used="test",
        )
    )
    db.commit()

    resp = client.post(f"/api/v1/emails/{email.id}/promote", json={})

    assert resp.status_code == 200
    assert resp.json()["created"] is False
    assert resp.json()["stage"] == "interview"
    db.refresh(application)
    assert application.stage == "interview"
