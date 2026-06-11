from datetime import UTC, datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app.db.models import Application, Company
from app.db.repositories.base import BaseRepository
from app.services.follow_up_service import FollowUpService


def _with_company(query):
    return query.options(joinedload(Application.company))


class ApplicationRepository(BaseRepository):
    def get_all(self) -> list[Application]:
        return _with_company(self.session.query(Application)).all()

    def get_by_id(self, application_id: int) -> Application | None:
        return (
            _with_company(self.session.query(Application))
            .filter(Application.id == application_id)
            .first()
        )

    def get_by_stage(self, stage: str) -> list[Application]:
        return (
            _with_company(self.session.query(Application))
            .filter(Application.stage == stage)
            .all()
        )

    def search(
        self,
        stage: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Application], int]:
        """Filter by stage and/or a search term (company name or position),
        returning a page of results plus the total match count for pagination.
        Uses ``.has()`` for the company match so it does not collide with the
        joinedload of the same relationship."""
        filters = []
        if stage:
            filters.append(Application.stage == stage)
        term = (q or "").strip()
        if term:
            like = f"%{term.lower()}%"
            filters.append(
                or_(
                    Application.company.has(func.lower(Company.name).like(like)),
                    func.lower(Application.position).like(like),
                )
            )
        total = self.session.query(Application).filter(*filters).count()
        items = (
            _with_company(self.session.query(Application).filter(*filters))
            .order_by(Application.applied_date.desc(), Application.id.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return items, total

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
            FollowUpService(self.session).recompute_last_contact_at(application)
        return application

    def update_stage(
        self, application: Application, new_stage: str | None, date: datetime | None
    ) -> None:
        if not new_stage or date is None:
            return
        date_naive = (
            date.astimezone(UTC).replace(tzinfo=None) if date.tzinfo else date
        )
        last_updated_naive = (
            application.last_updated.astimezone(UTC).replace(tzinfo=None)
            if application.last_updated.tzinfo
            else application.last_updated
        )
        if date_naive > last_updated_naive:
            application.stage = new_stage
            application.last_updated = date_naive
