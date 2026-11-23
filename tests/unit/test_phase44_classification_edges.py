"""Behavior tests for quick_filter and the post-model override.

Real application mail must reach classification. Alerts, newsletters, and
marketing must not. A model answer is not final when the wording is clear.
"""

import pytest

from app.email_client.application_signals import reconcile_classification
from app.email_client.quick_filter import quick_filter
from app.llm.base import EmailClassification
from app.services.email_service import EmailData

CONFIRMATION = (
    "Thank you for applying to the Backend Engineer role at Acme. "
    "We received your application."
)
REJECTION = (
    "Thank you for your interest. We will not be moving forward "
    "with your application for Backend Engineer at Acme."
)
INTERVIEW = "We would like to schedule an interview for the Backend Engineer role you applied for."
OFFER = "We are pleased to extend an offer of employment for the Backend Engineer role at Acme."
ASSESSMENT = (
    "Please complete this coding assessment for your application "
    "to the Backend Engineer role at Acme."
)

MARKETING_FOOTER = (
    "\n\n---\n"
    "You are receiving this job alert because of a saved search.\n"
    "Jobs you might like: Barista, Driver, Analyst.\n"
    "We're hiring engineers. Apply now. New jobs were posted today.\n"
    "Special offer: upgrade your job alerts.\n"
    "Unsubscribe from this newsletter.\n"
)

_EMPLOYER = "hr@acme.com"
_BOARDS = (
    "noreply@indeed.com",
    "jobs-noreply@linkedin.com",
    "notifications@greenhouse.io",
    "no-reply@myworkday.com",
)
_KINDS = (
    ("confirmation", "Application received", CONFIRMATION),
    ("rejection", "Update on your application", REJECTION),
    ("interview", "Next step", INTERVIEW),
    ("offer", "Your offer", OFFER),
    ("assessment", "Coding assessment", ASSESSMENT),
)


def _mail(sender: str, subject: str, body: str, *, uid: str = "44") -> EmailData:
    return EmailData(
        message_id=f"<{uid}@phase44.test>",
        uid=uid,
        sender=sender,
        subject=subject,
        date=None,
        body=body,
    )


class _Scripted:
    def __init__(self, result: EmailClassification | None) -> None:
        self.result = result
        self.provider_name = "scripted"
        self.calls = 0

    def classify_email(self, sender: str, subject: str, body: str) -> EmailClassification | None:
        self.calls += 1
        return self.result


def _model(is_application: bool, stage: str | None = None) -> EmailClassification:
    return EmailClassification(
        is_application=is_application,
        company="Acme",
        position="Backend Engineer",
        stage=stage,
        confidence="high",
    )


class TestQuickFilterLetsRealApplicationsThrough:
    @pytest.mark.parametrize("sender", (_EMPLOYER, *_BOARDS))
    @pytest.mark.parametrize(("kind", "subject", "body"), _KINDS)
    def test_confirmation_rejection_interview_offer_and_assessment(
        self, sender: str, kind: str, subject: str, body: str
    ):
        assert quick_filter(sender, subject, body) is True, f"{kind} from {sender}"

    def test_display_name_does_not_hide_an_indeed_confirmation(self):
        assert quick_filter(
            "Indeed <noreply@indeed.com>",
            "Application received",
            CONFIRMATION,
        ) is True

    def test_marketing_footer_does_not_cancel_a_confirmation(self):
        assert quick_filter(_EMPLOYER, "Application received", CONFIRMATION) is True
        assert quick_filter(
            _EMPLOYER,
            "Application received",
            CONFIRMATION + MARKETING_FOOTER,
        ) is True

    def test_marketing_footer_does_not_cancel_a_rejection(self):
        assert quick_filter(_EMPLOYER, "Update on your application", REJECTION) is True
        assert quick_filter(
            _EMPLOYER,
            "Update on your application",
            REJECTION + MARKETING_FOOTER,
        ) is True

    def test_board_subdomain_confirmation_gets_through(self):
        assert quick_filter(
            "jobs@mail.indeed.com",
            "Application received",
            CONFIRMATION,
        ) is True
        assert quick_filter(
            "jobs@notifications.greenhouse.io",
            "Application received",
            CONFIRMATION,
        ) is True


class TestQuickFilterKeepsMarketingOut:
    @pytest.mark.parametrize(
        ("sender", "subject", "body"),
        [
            (
                "alerts@indeed.com",
                "Job alert",
                "12 new jobs match your search. New positions available near you.",
            ),
            (
                "news@industry.test",
                "November newsletter",
                "Here is our monthly newsletter with industry news and events.",
            ),
            (
                "jobs-noreply@linkedin.com",
                "Jobs you might like",
                "Jobs you might like based on your profile.",
            ),
            (
                "talent@bigco.com",
                "We're hiring",
                "Hiring blast: we're hiring engineers across the company. Apply now.",
            ),
            (
                "deals@vendor.test",
                "Special offer",
                "Special offer: 50% off our recruiting suite this week only.",
            ),
        ],
    )
    def test_alerts_newsletters_hiring_blasts_and_special_offers_stay_out(
        self, sender: str, subject: str, body: str
    ):
        assert quick_filter(sender, subject, body) is False, subject

    def test_job_board_subdomain_alert_stays_out(self):
        assert quick_filter(
            "alerts@mail.indeed.com",
            "Job alert",
            "New jobs for you this week. Apply now.",
        ) is False
        assert quick_filter(
            "alerts@jobs.lever.co",
            "Job alert",
            "Open positions you might like. Apply now.",
        ) is False


class TestDomainSuffix:
    def test_clever_co_is_not_treated_as_lever(self):
        assert quick_filter("hr@clever.co", "Next step", INTERVIEW) is True

    def test_notindeed_com_is_not_treated_as_indeed(self):
        assert quick_filter("hr@notindeed.com", "Next step", INTERVIEW) is True

    def test_indeed_com_as_a_label_prefix_is_not_indeed(self):
        assert quick_filter("hr@indeed.com.evil.test", "Next step", INTERVIEW) is True

    def test_lever_co_as_a_label_prefix_is_not_lever(self):
        assert quick_filter("hr@lever.co.example.com", "Next step", INTERVIEW) is True

    def test_a_real_lever_subdomain_still_drops_a_job_alert(self):
        assert quick_filter(
            "alerts@mail.lever.co",
            "Job alert",
            "New jobs you might like. Apply now.",
        ) is False


class TestPostModelOverride:
    def test_model_no_is_not_final_for_an_unambiguous_rejection(self):
        email = _mail("talent@indeed.com", "Update on your application", REJECTION, uid="rej")
        classifier = _Scripted(_model(False))

        assert email.classify(classifier) is True
        assert email.is_application is True
        assert email.stage == "rejected"
        assert classifier.calls == 1

    def test_model_no_is_not_final_for_an_unambiguous_interview(self):
        email = _mail("notifications@greenhouse.io", "Next step", INTERVIEW, uid="int")
        classifier = _Scripted(_model(False))

        assert email.classify(classifier) is True
        assert email.is_application is True
        assert email.stage == "interview"
        assert classifier.calls == 1

    def test_model_no_is_not_final_when_a_footer_follows_a_confirmation(self):
        email = _mail(
            _EMPLOYER,
            "Application received",
            CONFIRMATION + MARKETING_FOOTER,
            uid="footer-yes",
        )
        classifier = _Scripted(_model(False))

        assert email.classify(classifier) is True
        assert email.is_application is True
        assert classifier.calls == 1

    def test_model_yes_is_not_final_for_a_job_alert(self):
        overridden = reconcile_classification(
            "alerts@indeed.com",
            "Job alert",
            "Jobs you might like this week. New jobs near you. Apply now.",
            _model(True, "applied"),
        )
        assert overridden is None or overridden.is_application is False

        email = _mail(
            "alerts@indeed.com",
            "Job alert",
            "Jobs you might like this week. New jobs near you. Apply now.",
            uid="alert",
        )
        classifier = _Scripted(_model(True, "applied"))
        assert email.classify(classifier) is False
        assert email.is_application is False

    def test_model_yes_is_not_final_for_a_newsletter(self):
        body = (
            "Weekly recruiting newsletter: interview tips, resume examples, "
            "and a special offer for candidates."
        )
        overridden = reconcile_classification(
            "news@industry.test",
            "November newsletter",
            body,
            _model(True, "applied"),
        )
        assert overridden is None or overridden.is_application is False

        email = _mail("news@industry.test", "November newsletter", body, uid="news")
        classifier = _Scripted(_model(True, "applied"))
        assert email.classify(classifier) is False
        assert email.is_application is False

    def test_model_yes_is_not_final_for_a_special_offer(self):
        overridden = reconcile_classification(
            "deals@vendor.test",
            "Special offer",
            "Special offer: 50% off our recruiting suite this week only.",
            _model(True, "applied"),
        )
        assert overridden is None or overridden.is_application is False


class TestGrayMail:
    _SENDER = "alex@example.com"
    _SUBJECT = "Document"
    _BODY = "Attached is the resume."

    @pytest.mark.xfail(
        reason=(
            "Expected a resume-only email to reach the model. "
            "quick_filter returned False and skipped it."
        )
    )
    def test_weak_keyword_mail_goes_to_the_model(self):
        assert quick_filter(self._SENDER, self._SUBJECT, self._BODY) is True
        email = _mail(self._SENDER, self._SUBJECT, self._BODY, uid="gray")
        classifier = _Scripted(_model(False))
        email.classify(classifier)
        assert classifier.calls == 1

    def test_weak_keyword_mail_is_not_forced_in_when_the_model_says_no(self):
        email = _mail(self._SENDER, self._SUBJECT, self._BODY, uid="gray-no")
        classifier = _Scripted(_model(False))

        assert email.classify(classifier) is False
        assert email.is_application is False

        overridden = reconcile_classification(
            self._SENDER,
            self._SUBJECT,
            self._BODY,
            _model(False),
        )
        assert overridden is None or overridden.is_application is False

    @pytest.mark.xfail(
        reason=(
            "Expected a model yes on resume-only mail to stand. "
            "quick_filter returned False, so classify() stored is_application False "
            "and never called the model."
        )
    )
    def test_weak_keyword_mail_keeps_a_model_yes(self):
        email = _mail(self._SENDER, self._SUBJECT, self._BODY, uid="gray-yes")
        classifier = _Scripted(_model(True, "applied"))

        assert email.classify(classifier) is True
        assert email.is_application is True
        assert classifier.calls == 1
