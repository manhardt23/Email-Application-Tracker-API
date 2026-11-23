"""Opening the job finder 500s when job_suggestions has no dismissed column.

Production is still the phase-34 table. GET /api/v1/finder/suggestions filters
on dismissed, Postgres reports ``column job_suggestions.dismissed does not exist``,
and the page shows the failed request. Startup applies
migrations/005_drop_finder_profile.sql so the same request returns the stored rows.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.router import api_router
from app.auth.dependencies import get_current_user, get_db, require_admin
from app.db.models import Base, User
from app.main import create_app

_ADMIN = User(id=1, username="admin", password_hash="x", role="admin")


def _phase34_finder_database():
    """job_suggestions as migrations/004 created it, plus the dropped profile table."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE qualification_profiles (
                    id INTEGER PRIMARY KEY,
                    target_titles TEXT NOT NULL DEFAULT '',
                    skills TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE job_suggestions (
                    id INTEGER PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    company_name VARCHAR(255) NOT NULL,
                    pay VARCHAR(255),
                    requirements_summary TEXT NOT NULL DEFAULT '',
                    apply_url VARCHAR(2000) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO job_suggestions
                    (title, company_name, pay, requirements_summary, apply_url)
                VALUES
                    ('Backend Engineer', 'Acme', NULL, 'Python', 'https://acme.example/apply')
                """
            )
        )
    # Other tables exist in production. create_all leaves the old job_suggestions table.
    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("job_suggestions")}
    assert "dismissed" not in columns
    assert "qualification_profiles" in inspect(engine).get_table_names()
    return engine


def _unmigrated_client(engine, *, raise_server_exceptions: bool = True) -> TestClient:
    """Finder routes against the phase-34 schema, with no startup migration."""
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: _ADMIN
    app.dependency_overrides[require_admin] = lambda: _ADMIN
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def test_finder_suggestions_on_database_missing_dismissed_column(monkeypatch):
    engine = _phase34_finder_database()
    # Opening the job finder calls this. Postgres: column job_suggestions.dismissed
    # does not exist. That unhandled error is the production 500.
    failed = _unmigrated_client(engine, raise_server_exceptions=False).get(
        "/api/v1/finder/suggestions"
    )
    assert failed.status_code == 500
    with pytest.raises(OperationalError, match="no such column: job_suggestions.dismissed"):
        _unmigrated_client(engine).get("/api/v1/finder/suggestions")

    monkeypatch.setattr("app.main.engine", engine)
    monkeypatch.setattr(
        "app.auth.dependencies.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=engine),
    )

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: _ADMIN
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    with TestClient(app) as client:
        listed = client.get("/api/v1/finder/suggestions")

    assert listed.status_code == 200
    assert listed.json() == [
        {
            "id": 1,
            "title": "Backend Engineer",
            "company": "Acme",
            "pay": None,
            "requirements_summary": "Python",
            "apply_url": "https://acme.example/apply",
        }
    ]
    columns = {column["name"] for column in inspect(engine).get_columns("job_suggestions")}
    assert "dismissed" in columns
    assert "qualification_profiles" not in inspect(engine).get_table_names()
