"""Apply SQL that create_all cannot apply to an existing database."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
FINDER_PROFILE_MIGRATION = "005_drop_finder_profile.sql"


def _statements(script: str) -> list[str]:
    lines = [line for line in script.splitlines() if not line.strip().startswith("--")]
    return [part.strip() for part in "\n".join(lines).split(";") if part.strip()]


def apply_drop_finder_profile(engine: Engine) -> None:
    """Run migrations/005_drop_finder_profile.sql.

    create_all does not add columns to a table that already exists. Production
    still has the phase-34 job_suggestions table, so the finder list filter on
    dismissed raises ``column job_suggestions.dismissed does not exist`` and
    GET /api/v1/finder/suggestions returns 500.

    Postgres runs the migration file. SQLite tests use the same change without
    ``ADD COLUMN IF NOT EXISTS``, which SQLite rejects.
    """
    script = (_MIGRATIONS / FINDER_PROFILE_MIGRATION).read_text()
    if engine.dialect.name == "postgresql":
        statements = _statements(script)
    else:
        statements = _sqlite_statements(engine, script)
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    logger.info("Applied %s", FINDER_PROFILE_MIGRATION)


def _sqlite_statements(engine: Engine, script: str) -> list[str]:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    statements: list[str] = []
    if "qualification_profiles" in tables:
        statements.append("DROP TABLE qualification_profiles")
    if "job_suggestions" not in tables:
        return statements
    columns = {column["name"] for column in inspector.get_columns("job_suggestions")}
    if "dismissed" in columns:
        return statements
    alter = next(
        (statement for statement in _statements(script) if statement.upper().startswith("ALTER")),
        None,
    )
    if alter is None:
        return statements
    # SQLite parses `IF NOT EXISTS` on CREATE TABLE, not on ADD COLUMN.
    statements.append(alter.replace("IF NOT EXISTS ", "", 1))
    return statements
