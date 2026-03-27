from sqlalchemy import func
from app.db.models import Company
from app.db.repositories.base import BaseRepository


class CompanyRepository(BaseRepository):
    def find_by_name(self, name: str) -> Company | None:
        return (
            self.session.query(Company)
            .filter(func.lower(Company.name) == name.lower())
            .first()
        )

    def find_or_create(self, name: str) -> Company:
        company = self.find_by_name(name)
        if not company:
            company = Company(name=name)
            self.session.add(company)
            self.session.flush()
        return company
