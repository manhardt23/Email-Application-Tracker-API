"""The production URL is postgresql://, which SQLAlchemy 2.1 loads with psycopg v3.

create_engine imports that module before it connects. If the image does not
include it, uvicorn exits and the container never listens.
"""

import psycopg
from sqlalchemy import create_engine


def test_default_postgres_url_imports_psycopg():
    engine = create_engine("postgresql://user:pass@db:5432/job_tracker")
    try:
        assert engine.dialect.driver == "psycopg"
        assert engine.dialect.dbapi is psycopg
    finally:
        engine.dispose()
