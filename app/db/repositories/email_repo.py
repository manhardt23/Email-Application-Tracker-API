from app.db.models import ApplicationEmail
from app.db.repositories.base import BaseRepository


class EmailRepository(BaseRepository):
    def find_by_uid(self, uid: str) -> ApplicationEmail | None:
        return (
            self.session.query(ApplicationEmail)
            .filter(ApplicationEmail.email_id == uid)
            .first()
        )

    def get_all(self) -> list[ApplicationEmail]:
        return self.session.query(ApplicationEmail).all()

    def get_needs_review(self) -> list[ApplicationEmail]:
        return (
            self.session.query(ApplicationEmail)
            .filter(ApplicationEmail.needs_review == True)  # noqa: E712
            .all()
        )

    def create_from_email_data(self, email_data) -> ApplicationEmail:
        record = ApplicationEmail(
            email_id=email_data.uid,
            sender=email_data.sender,
            subject=email_data.subject,
            received_date=email_data.date,
            email_body=email_data.body,
            detected_company=email_data.company,
            detected_position=email_data.position,
            detected_stage=email_data.stage,
            is_application=email_data.is_application,
            confidence=email_data.confidence,
            needs_review=email_data.confidence == "low",
        )
        self.session.add(record)
        return record

    def link_to_application(self, email_record: ApplicationEmail, application_id: int) -> None:
        email_record.application_id = application_id
