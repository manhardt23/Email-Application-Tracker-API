from datetime import datetime, timezone
from sqlalchemy import func
from app.db.models import Application
from app.db.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository):
    def get_all(self) -> list[Application]:
        return self.session.query(Application).all()

    def get_by_id(self, application_id: int) -> Application | None:
        return self.session.query(Application).filter(Application.id == application_id).first()

    def get_by_stage(self, stage: str) -> list[Application]:
        return self.session.query(Application).filter(Application.stage == stage).all()

    def find_by_company_and_position(self, company_id: int, position: str) -> Application | None:
        return (
            self.session.query(Application)
            .filter(
                Application.company_id == company_id,
                func.lower(Application.position) == position.lower(),
            )
            .first()
        )

    def find_or_create(self, company_id: int, position: str) -> Application:
        application = self.find_by_company_and_position(company_id, position)
        if not application:
            application = Application(company_id=company_id, position=position, stage="applied")
            self.session.add(application)
            self.session.flush()
        return application

    def update_stage(
        self, application: Application, new_stage: str | None, date: datetime | None
    ) -> None:
        if not new_stage or date is None:
            return
        date_naive = (
            date.astimezone(timezone.utc).replace(tzinfo=None) if date.tzinfo else date
        )
        last_updated_naive = (
            application.last_updated.astimezone(timezone.utc).replace(tzinfo=None)
            if application.last_updated.tzinfo
            else application.last_updated
        )
        if date_naive > last_updated_naive:
            application.stage = new_stage
            application.last_updated = date_naive
