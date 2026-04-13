"""
Additional API endpoint tests for paths not covered by test_phase5_api.py.

Covers: GET /health, GET /applications (list + stage filter + 404),
        GET /applications/{id}.
Uses shared conftest fixtures.
"""
from datetime import datetime

import pytest

from app.db.models import Application, Company


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_application(db, stage="applied", company_name="Acme"):
    company = Company(name=company_name)
    db.add(company)
    db.flush()
    application = Application(company_id=company.id, position="Engineer", stage=stage)
    db.add(application)
    db.commit()
    return application


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health_returns_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /applications
# ---------------------------------------------------------------------------


def test_list_applications_returns_all(client, db):
    _seed_application(db, stage="applied", company_name="A Corp")
    _seed_application(db, stage="interview", company_name="B Corp")

    resp = client.get("/api/v1/applications")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_applications_empty_returns_404(client):
    resp = client.get("/api/v1/applications")
    assert resp.status_code == 404


def test_list_applications_filter_by_stage(client, db):
    _seed_application(db, stage="applied", company_name="A Corp")
    _seed_application(db, stage="offer", company_name="B Corp")

    resp = client.get("/api/v1/applications?stage=offer")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["stage"] == "offer"


def test_list_applications_filter_by_stage_not_found(client, db):
    _seed_application(db, stage="applied")

    resp = client.get("/api/v1/applications?stage=offer")

    assert resp.status_code == 404
    assert "offer" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /applications/{id}
# ---------------------------------------------------------------------------


def test_get_application_returns_correct_record(client, db):
    app = _seed_application(db)

    resp = client.get(f"/api/v1/applications/{app.id}")

    assert resp.status_code == 200
    assert resp.json()["stage"] == "applied"


def test_get_application_404_for_missing(client):
    resp = client.get("/api/v1/applications/9999")
    assert resp.status_code == 404
