from sqlalchemy.orm import Session

from app.db.models import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def find_by_username(self, username: str) -> User | None:
        return self.session.query(User).filter(User.username == username).first()

    def create(self, username: str, password_hash: str, role: str = "viewer") -> User:
        user = User(username=username, password_hash=password_hash, role=role)
        self.session.add(user)
        self.session.flush()
        return user
