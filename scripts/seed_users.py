"""
Seed admin and demo viewer accounts.

Usage (run once on EC2 after 003_users.sql migration):
    python -m scripts.seed_users

Required env: DATABASE_URL, SEED_ADMIN_USERNAME, SEED_ADMIN_PASSWORD,
              SEED_VIEWER_USERNAME, SEED_VIEWER_PASSWORD

If a username already exists it is skipped (idempotent).
"""
import os
import sys

# Allow running as `python -m scripts.seed_users` from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.auth.hashing import hash_password  # noqa: E402
from app.db import models  # noqa: E402
from app.db.database import SessionLocal, engine  # noqa: E402
from app.db.repositories.user_repo import UserRepository  # noqa: E402


def _require(var: str) -> str:
    val = os.environ.get(var)
    if not val:
        print(f"ERROR: {var} is not set", file=sys.stderr)
        sys.exit(1)
    return val


def seed() -> None:
    models.Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    repo = UserRepository(session)

    accounts = [
        (
            _require("SEED_ADMIN_USERNAME"),
            _require("SEED_ADMIN_PASSWORD"),
            "admin",
        ),
        (
            _require("SEED_VIEWER_USERNAME"),
            _require("SEED_VIEWER_PASSWORD"),
            "viewer",
        ),
    ]

    try:
        for username, password, role in accounts:
            if repo.find_by_username(username):
                print(f"User '{username}' already exists — skipping")
                continue
            repo.create(username, hash_password(password), role)
            print(f"Created {role} user '{username}'")
        session.commit()
        print("Done.")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
