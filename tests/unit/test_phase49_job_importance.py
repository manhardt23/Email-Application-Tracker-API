"""Phase 49 — assistant-set importance_score on job suggestions."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from mcp.server.fastmcp.exceptions import ToolError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, require_admin
from app.db.ensure_schema import apply_job_importance_score
from app.db.models import Base, JobSuggestion, User
from app.main import create_app
from app.mcp.server import _INSTRUCTIONS
from app.mcp.tools import create_job_suggestion, list_job_suggestions, update_job_suggestion
from app.services.job_finder import SuggestionError, create_suggestion, update_suggestion

_ADMIN = User(id=1, username="admin", password_hash="x", role="admin")


def test_mcp_instructions_ask_for_an_importance_score():
    assert "no fit score" not in _INSTRUCTIONS
    assert "importance_score" in _INSTRUCTIONS
    assert "0 to 100" in _INSTRUCTIONS
    assert "Jacob apply" in _INSTRUCTIONS
    assert "does not calculate" in _INSTRUCTIONS


def test_create_and_update_accept_a_score_and_reject_out_of_range(db):
    created = create_suggestion(
        db,
        title="Analyst",
        company="Initech",
        apply_url="https://initech.example/jobs",
        importance_score=85,
    )
    assert created["importance_score"] == 85

    omitted = create_suggestion(
        db,
        title="Writer",
        company="Initech",
        apply_url="https://initech.example/write",
    )
    assert omitted["importance_score"] is None

    top = create_suggestion(
        db,
        title="Director",
        company="Initech",
        apply_url="https://initech.example/director",
        importance_score=100,
    )
    assert top["importance_score"] == 100

    updated = update_suggestion(db, created["id"], {"importance_score": 55})
    assert updated["importance_score"] == 55
    zero = update_suggestion(db, created["id"], {"importance_score": 0})
    assert zero["importance_score"] == 0

    unchanged = update_suggestion(db, created["id"], {"title": "Senior Analyst"})
    assert unchanged["title"] == "Senior Analyst"
    assert unchanged["importance_score"] == 0

    for bad in (-1, 101):
        with pytest.raises(SuggestionError, match="0 to 100"):
            create_suggestion(
                db,
                title="Bad",
                company="Initech",
                apply_url="https://initech.example/bad",
                importance_score=bad,
            )
        with pytest.raises(SuggestionError, match="0 to 100"):
            update_suggestion(db, created["id"], {"importance_score": bad})

    db.expire_all()
    stored = db.get(JobSuggestion, created["id"])
    assert stored.importance_score == 0
    assert stored.title == "Senior Analyst"


def test_mcp_tools_set_score_and_omit_leaves_it(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr("app.mcp.tools.session_factory", factory)

    created = create_job_suggestion(
        title="Analyst",
        company="Initech",
        apply_url="https://initech.example/jobs",
        importance_score=85,
    )
    assert created["importance_score"] == 85

    omitted = create_job_suggestion(
        title="Writer",
        company="Initech",
        apply_url="https://initech.example/write",
    )
    assert omitted["importance_score"] is None

    renamed = update_job_suggestion(created["id"], title="Senior Analyst")
    assert renamed["title"] == "Senior Analyst"
    assert renamed["importance_score"] == 85

    rescored = update_job_suggestion(created["id"], importance_score=55)
    assert rescored["importance_score"] == 55

    with pytest.raises(ToolError, match="0 to 100"):
        create_job_suggestion(
            title="Low",
            company="Initech",
            apply_url="https://initech.example/low",
            importance_score=-1,
        )
    with pytest.raises(ToolError, match="0 to 100"):
        create_job_suggestion(
            title="High",
            company="Initech",
            apply_url="https://initech.example/high",
            importance_score=101,
        )
    with pytest.raises(ToolError, match="0 to 100"):
        update_job_suggestion(created["id"], importance_score=-1)
    with pytest.raises(ToolError, match="0 to 100"):
        update_job_suggestion(created["id"], importance_score=101)

    listed = list_job_suggestions()
    assert [(item["title"], item["importance_score"]) for item in listed["items"]] == [
        ("Senior Analyst", 55),
        ("Writer", None),
    ]


def test_list_orders_high_mid_low_then_unscored(client, db):
    base = datetime(2026, 1, 1, tzinfo=UTC)
    rows = [
        ("Unscored Old", None, 0),
        ("Low", 20, 1),
        ("Zero", 0, 2),
        ("Unscored New", None, 3),
        ("High", 85, 4),
        ("Mid", 55, 5),
    ]
    for title, score, offset in rows:
        db.add(
            JobSuggestion(
                title=title,
                company_name="Acme",
                pay=None,
                requirements_summary="",
                apply_url=f"https://acme.example/{offset}",
                importance_score=score,
                created_at=base + timedelta(hours=offset),
            )
        )
    db.commit()

    listed = client.get("/api/v1/finder/suggestions").json()
    assert [(item["title"], item["importance_score"]) for item in listed] == [
        ("High", 85),
        ("Mid", 55),
        ("Low", 20),
        ("Zero", 0),
        ("Unscored New", None),
        ("Unscored Old", None),
    ]


def _table_without_importance_score():
    """job_suggestions after phase 41: dismissed exists, importance_score does not."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
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
                    dismissed BOOLEAN NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO job_suggestions
                    (title, company_name, pay, requirements_summary, apply_url, dismissed)
                VALUES
                    ('Backend Engineer', 'Acme', NULL, 'Python', 'https://acme.example/apply', 0)
                """
            )
        )
    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("job_suggestions")}
    assert "dismissed" in columns
    assert "importance_score" not in columns
    return engine


def test_migration_adds_importance_score_when_the_column_is_missing():
    engine = _table_without_importance_score()
    apply_job_importance_score(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("job_suggestions")}
    assert "importance_score" in columns
    with engine.connect() as connection:
        stored = connection.execute(text("SELECT importance_score FROM job_suggestions")).scalar()
    assert stored is None
    apply_job_importance_score(engine)


def test_startup_adds_importance_score_on_a_table_that_lacks_it(monkeypatch):
    engine = _table_without_importance_score()
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
    assert listed.json()[0]["title"] == "Backend Engineer"
    assert listed.json()[0]["importance_score"] is None
    columns = {column["name"] for column in inspect(engine).get_columns("job_suggestions")}
    assert "importance_score" in columns
