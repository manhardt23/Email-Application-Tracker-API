import logging
from datetime import datetime
from time import perf_counter

from app.email_client.application_signals import reconcile_classification
from app.email_client.client import fetch_emails_by_date_range, fetch_recent_emails
from app.email_client.quick_filter import quick_filter
from app.llm.base import EmailClassification, LLMClassifier
from app.llm.errors import LLMResponseError

logger = logging.getLogger(__name__)


class EmailData:
    """Holds a single email's raw data and LLM classification results."""

    def __init__(
        self,
        message_id: str | None,
        uid: str,
        sender: str,
        subject: str,
        date: datetime | None,
        body: str,
    ) -> None:
        self.message_id = message_id
        self.uid = uid
        self.sender = sender
        self.subject = subject
        self.date = date
        self.body = body

        # Populated after classify()
        self.is_application: bool | None = None
        self.company: str | None = None
        self.position: str | None = None
        self.stage: str | None = None
        self.confidence: str | None = None

    def classify(self, classifier: LLMClassifier) -> bool:
        """Run LLM classification. Returns True if the email is a job application."""
        provider = getattr(classifier, "provider_name", "unknown")
        if not quick_filter(self.sender, self.subject, self.body):
            logger.debug(
                "quick_filter=rejected provider=%s latency_ms=0 outcome=filtered", provider
            )
            self.is_application = False
            return False

        start = perf_counter()
        unreadable = False
        try:
            result: EmailClassification | None = classifier.classify_email(
                self.sender, self.subject, self.body
            )
        except LLMResponseError:
            # This message's reply was not JSON. Raising here fails the whole
            # check before any row is saved and leaves the UID cursor unchanged,
            # so every later run fetches the same window and dies on this mail.
            # Text rules below still accept an explicit rejection or interview.
            unreadable = True
            result = None
        latency_ms = (perf_counter() - start) * 1000
        result = reconcile_classification(self.sender, self.subject, self.body, result)
        if result is None:
            logger.warning(
                "LLM classify provider=%s latency_ms=%.2f uid=%s outcome=%s",
                provider,
                latency_ms,
                self.uid,
                "unreadable_response" if unreadable else "no_classification",
            )
            self.is_application = False
            return False

        self.is_application = result.is_application
        self.company = result.company
        self.position = result.position
        self.stage = result.stage
        self.confidence = result.confidence
        logger.info(
            "LLM classify provider=%s latency_ms=%.2f outcome=%s confidence=%s",
            provider,
            latency_ms,
            bool(result.is_application),
            result.confidence,
        )
        return bool(result.is_application)

    def __repr__(self) -> str:
        return (
            f"EmailData(uid={self.uid!r}, sender={self.sender!r}, "
            f"is_application={self.is_application}, company={self.company!r}, "
            f"confidence={self.confidence!r})"
        )


class EmailProcessor:
    """Fetches emails from IMAP and runs LLM classification on each."""

    def __init__(self, classifier: LLMClassifier) -> None:
        self.classifier = classifier
        self.email_list: list[EmailData] = []
        self.application_emails: list[EmailData] = []

    def fetch_emails(
        self,
        limit: int,
        since_uid: int = 1,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[EmailData]:
        if from_date is not None:
            raw_emails = fetch_emails_by_date_range(
                limit=limit,
                from_date=from_date,
                to_date=to_date,
            )
        else:
            raw_emails = fetch_recent_emails(limit, since_uid=since_uid)
        self.email_list = [
            EmailData(
                message_id=raw.get("message_id"),
                uid=raw["uid"],
                sender=raw["sender"],
                subject=raw["subject"],
                body=raw["body"],
                date=raw["date"],
            )
            for raw in raw_emails
        ]
        logger.info("Fetched %d emails from IMAP", len(self.email_list))
        return self.email_list

    def analyze_emails(self) -> list[EmailData]:
        for email_data in self.email_list:
            if email_data.classify(self.classifier):
                self.application_emails.append(email_data)
            else:
                logger.debug("Not an application email — skipped")
        return self.application_emails

    def get_high_confidence(self) -> list[EmailData]:
        return [e for e in self.application_emails if e.confidence == "high"]

    def get_needs_review(self) -> list[EmailData]:
        return [e for e in self.application_emails if e.confidence == "low"]
