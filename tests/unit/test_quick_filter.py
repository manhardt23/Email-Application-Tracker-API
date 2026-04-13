"""
Unit tests for app.email_client.quick_filter.

Tests cover: job-board domain filtering, job-posting pattern rejection,
keyword scoring, application-confirmation pass-through.
"""
from app.email_client.quick_filter import quick_filter


class TestQuickFilterJobBoards:
    def test_job_board_without_confirmation_rejected(self):
        assert quick_filter(
            sender="noreply@indeed.com",
            subject="New jobs for you",
            email_content="Many new positions available near you.",
        ) is False

    def test_job_board_with_confirmation_passes(self):
        assert quick_filter(
            sender="noreply@linkedin.com",
            subject="Application received",
            email_content="Thank you for applying. We received your application.",
        ) is True

    def test_non_job_board_domain_not_filtered_by_domain_rule(self):
        # Direct employer email with keyword hits should pass
        result = quick_filter(
            sender="hr@somecompany.com",
            subject="Your application",
            email_content="Thank you for applying. Next steps will follow.",
        )
        assert result is True


class TestQuickFilterJobPostingPatterns:
    def test_generic_posting_rejected(self):
        assert quick_filter(
            sender="jobs@board.com",
            subject="We're hiring engineers",
            email_content="We have open positions for software engineers. Apply now.",
        ) is False

    def test_job_posting_with_application_status_passes(self):
        # Ambiguous: posting language but also mentions "your application"
        result = quick_filter(
            sender="hr@company.com",
            subject="Next steps — your application",
            email_content="New role available. Your application has been submitted.",
        )
        assert result is True


class TestQuickFilterKeywordScore:
    def test_two_keyword_hits_pass(self):
        assert quick_filter(
            sender="hr@company.com",
            subject="candidate update",
            email_content="Your application has been received.",
        ) is True

    def test_single_weak_keyword_returns_false(self):
        assert quick_filter(
            sender="noreply@company.com",
            subject="Newsletter",
            email_content="Check out our latest updates this week.",
        ) is False


class TestQuickFilterConfirmationPatterns:
    def test_thank_you_for_applying_passes(self):
        assert quick_filter(
            sender="hr@company.com",
            subject="Thanks",
            email_content="Thank you for applying to our team.",
        ) is True

    def test_application_status_update_passes(self):
        assert quick_filter(
            sender="hr@company.com",
            subject="Application status",
            email_content="We want to share an application status update with you.",
        ) is True

    def test_interview_invitation_passes(self):
        assert quick_filter(
            sender="hr@company.com",
            subject="Interview invitation",
            email_content="You have an interview invitation regarding your application.",
        ) is True


class TestExtractDomain:
    def test_no_at_sign_does_not_crash(self):
        # sender with no @ — domain extraction returns None, no crash
        result = quick_filter(
            sender="no-at-sign",
            subject="offer",
            email_content="candidate application next steps",
        )
        # Result could be True or False; just ensure no exception
        assert isinstance(result, bool)
