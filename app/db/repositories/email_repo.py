from datetime import datetime

from app.db.models import Email
from app.db.repositories.base import BaseRepository


class EmailRepository(BaseRepository):
    def find_by_message_id(self, message_id: str) -> Email | None:
        return (
            self.session.query(Email)
            .filter(Email.message_id == message_id)
            .first()
        )

    def find_by_uid(self, uid: str) -> Email | None:
        return self.session.query(Email).filter(Email.uid == uid).first()

    def exists(self, message_id: str | None, uid: str) -> bool:
        if message_id and self.find_by_message_id(message_id):
            return True
        return self.find_by_uid(uid) is not None

    def create(
        self,
        message_id: str | None,
        uid: str,
        sender: str,
        subject: str,
        body: str,
        received_date: datetime,
    ) -> Email:
        record = Email(
            message_id=message_id,
            uid=uid,
            sender=sender,
            subject=subject,
            body=body,
            received_date=received_date,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_all(self) -> list[Email]:
        return self.session.query(Email).all()
