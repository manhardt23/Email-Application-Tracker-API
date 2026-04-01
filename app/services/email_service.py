from datetime import datetime

from app.email_client.client import fetch_recent_emails
from app.llm.base import EmailClassification, LLMClassifier


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
        result: EmailClassification | None = classifier.classify_email(
            self.sender, self.subject, self.body
        )
        if result is None:
            self.is_application = False
            return False
        self.is_application = result.is_application
        self.company = result.company
        self.position = result.position
        self.stage = result.stage
        self.confidence = result.confidence
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

    def fetch_emails(self, limit: int) -> list[EmailData]:
        raw_emails = fetch_recent_emails(limit)
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
        print(f"Fetched {len(self.email_list)} emails")
        return self.email_list

    def analyze_emails(self) -> list[EmailData]:
        for email_data in self.email_list:
            if email_data.classify(self.classifier):
                self.application_emails.append(email_data)
            else:
                print("Not an application email — skipped")
        return self.application_emails

    def get_high_confidence(self) -> list[EmailData]:
        return [e for e in self.application_emails if e.confidence == "high"]

    def get_needs_review(self) -> list[EmailData]:
        return [e for e in self.application_emails if e.confidence == "low"]
