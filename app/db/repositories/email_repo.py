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

    def find_match_reason(self, message_id: str | None, uid: str) -> tuple[str, Email] | None:
        if message_id:
            matched = self.find_by_message_id(message_id)
            if matched:
                return ("message_id", matched)
        matched = self.find_by_uid(uid)
        if matched:
            return ("uid", matched)
        return None

    def exists(self, message_id: str | None, uid: str) -> bool:
        return self.find_match_reason(message_id, uid) is not None

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
        return (
            self.session.query(Email)
            .order_by(Email.received_date.desc())
            .all()
        )
