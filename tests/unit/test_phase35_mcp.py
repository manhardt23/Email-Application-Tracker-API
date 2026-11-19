"""Phase 35 — MCP bearer auth and the job-finder tools exposed to Grok."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.fastmcp.exceptions import ToolError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.jwt_handler import create_access_token
from app.config import get_settings
from app.db.models import Application, Base, Company
from app.main import create_app
from app.mcp.auth import credential_is_valid
from app.mcp.tools import update_job_finder_profile
from app.services.job_finder import SuggestionError, create_suggestion, update_suggestion

SECRET = "phase35-mcp-secret"
TOOL_NAMES = {
    "list_applications",
    "get_application",
    "list_job_suggestions",
    "create_job_suggestion",
    "update_job_suggestion",
    "get_job_finder_profile",
    "update_job_finder_profile",
}


@pytest.fixture()
def mcp_secret(monkeypatch):
    monkeypatch.setenv("MCP_BEARER_TOKEN", SECRET)
    get_settings.cache_clear()
    yield SECRET
    get_settings.cache_clear()


@pytest.fixture()
def memory_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr("app.mcp.tools.session_factory", factory)
    session = factory()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_missing_and_wrong_credential_are_rejected(mcp_secret):
    app = create_app()
    admin_jwt = create_access_token("admin", "admin")
    viewer_jwt = create_access_token("viewer", "viewer")
    with TestClient(app) as client:
        missing = client.post("/mcp")
        wrong = client.post("/mcp", headers=_auth("not-the-secret"))
        admin = client.post("/mcp", headers=_auth(admin_jwt))
        viewer = client.post("/mcp", headers=_auth(viewer_jwt))
        health = client.get("/api/v1/health")

    for response in (missing, wrong, admin, viewer):
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing MCP credential"
        assert response.headers["www-authenticate"] == "Bearer"
    assert health.status_code == 200


def test_unconfigured_secret_rejects_every_call(monkeypatch):
    monkeypatch.delenv("MCP_BEARER_TOKEN", raising=False)
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        response = client.post("/mcp", headers=_auth(SECRET))
    assert response.status_code == 401
    assert credential_is_valid(f"Bearer {SECRET}") is False
    get_settings.cache_clear()


def test_api_serves_when_mcp_token_unset_and_rate_limit_is_on(monkeypatch):
    """Production leaves the limiter on. conftest turns it off, which hid a 500.

    slowapi looks up endpoint.__name__ before the bearer check. The MCP ASGI
    app had none, so /mcp returned 500 while the token was unset. Startup must
    not require MCP_BEARER_TOKEN: /mcp is 401 and the rest of the API still serves.
    """
    from app.middleware.rate_limit import limiter

    monkeypatch.delenv("MCP_BEARER_TOKEN", raising=False)
    get_settings.cache_clear()
    previous = limiter.enabled
    limiter.enabled = True
    try:
        app = create_app()
        with TestClient(app) as client:
            health = client.get("/api/v1/health")
            missing = client.post("/mcp")
            presented = client.post("/mcp", headers=_auth(SECRET))
            still_up = client.get("/api/v1/health")
    finally:
        limiter.enabled = previous
        get_settings.cache_clear()

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    for response in (missing, presented):
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing MCP credential"
        assert response.headers["www-authenticate"] == "Bearer"
    assert still_up.status_code == 200
    assert credential_is_valid(f"Bearer {SECRET}") is False


def test_profile_text_over_limit_is_rejected():
    with pytest.raises(ToolError, match="4000"):
        update_job_finder_profile(target_titles="x" * 4001)


def test_create_rejects_bad_url_duplicate_and_existing_application(db):
    with pytest.raises(SuggestionError, match="http or https"):
        create_suggestion(
            db,
            title="Engineer",
            company="Acme",
            apply_url="javascript:alert(1)",
        )

    created = create_suggestion(
        db,
        title="Engineer",
        company="Acme",
        apply_url="https://acme.example/jobs",
        pay="$10",
    )
    with pytest.raises(SuggestionError, match="already exists"):
        create_suggestion(
            db,
            title="engineer",
            company="Acme",
            apply_url="https://acme.example/other",
        )

    company = Company(name="Globex")
    db.add(company)
    db.commit()
    db.add(Application(company_id=company.id, position="Analyst", stage="applied"))
    db.commit()
    with pytest.raises(SuggestionError, match="already an application"):
        create_suggestion(
            db,
            title="Analyst",
            company="Globex",
            apply_url="https://globex.example/jobs",
        )

    cleared = update_suggestion(db, created["id"], {"pay": ""})
    assert cleared["pay"] is None
    renamed = update_suggestion(db, created["id"], {"title": "Senior Engineer"})
    assert renamed["title"] == "Senior Engineer"
    with pytest.raises(SuggestionError, match="not found"):
        update_suggestion(db, 999999, {"title": "Nope"})
    with pytest.raises(SuggestionError, match="field to update"):
        update_suggestion(db, created["id"], {})


def _payload(result) -> dict | list:
    assert result.isError is False, result.content
    return json.loads(result.content[0].text)


def test_valid_credential_can_list_applications(mcp_secret, memory_session):
    company = Company(name="Acme")
    memory_session.add(company)
    memory_session.commit()
    memory_session.add(
        Application(company_id=company.id, position="Engineer", stage="interview")
    )
    memory_session.commit()
    memory_session.close()
    app = create_app()

    async def _call() -> None:
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers=_auth(mcp_secret),
            ) as http:
                async with streamable_http_client(
                    "http://testserver/mcp",
                    http_client=http,
                    terminate_on_close=False,
                ) as (read, write, _session_id):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        listed = await session.list_tools()
                        assert {tool.name for tool in listed.tools} == TOOL_NAMES

                        applications = _payload(await session.call_tool("list_applications", {}))
                        assert applications["total"] == 1
                        item = applications["items"][0]
                        assert item["company"] == "Acme"
                        assert item["title"] == "Engineer"
                        assert item["stage"] == "interview"

                        one = _payload(
                            await session.call_tool(
                                "get_application", {"application_id": item["id"]}
                            )
                        )
                        assert one["title"] == "Engineer"
                        missing = await session.call_tool(
                            "get_application", {"application_id": 999999}
                        )
                        assert missing.isError is True

                        profile = _payload(await session.call_tool("get_job_finder_profile", {}))
                        assert profile == {"target_titles": "", "skills": ""}
                        saved = _payload(
                            await session.call_tool(
                                "update_job_finder_profile",
                                {"target_titles": "Engineer", "skills": "Python"},
                            )
                        )
                        assert saved == {"target_titles": "Engineer", "skills": "Python"}

                        created = _payload(
                            await session.call_tool(
                                "create_job_suggestion",
                                {
                                    "title": "Analyst",
                                    "company": "Initech",
                                    "apply_url": "https://initech.example/jobs",
                                    "pay": "120k",
                                },
                            )
                        )
                        assert created["company"] == "Initech"
                        updated = _payload(
                            await session.call_tool(
                                "update_job_suggestion",
                                {"suggestion_id": created["id"], "title": "Senior Analyst"},
                            )
                        )
                        assert updated["title"] == "Senior Analyst"
                        suggestions = _payload(await session.call_tool("list_job_suggestions", {}))
                        assert suggestions["items"][0]["title"] == "Senior Analyst"
                        assert suggestions["items"][0]["company"] == "Initech"

    asyncio.run(_call())
