"""Phase 34 — job finder fit, exclusion of existing applications, and the API."""

import json
from types import SimpleNamespace

import httpx
import pytest

from app.db.models import Application, Company, JobSuggestion
from app.llm.errors import FinderError
from app.llm.xai_finder import SuggestedJob, build_prompt, fetch_job_suggestions, parse_suggestions
from app.services.job_finder import MISSING_XAI_KEY_DETAIL
from app.services.qualification_fit import (
    FIT_GAP,
    FIT_MET,
    FIT_PARTIAL,
    normalize_label,
    role_key,
    summarize_fit,
)


def _settings(*, api_key: str | None):
    return SimpleNamespace(
        xai_api_key=api_key,
        xai_model="grok-3",
        xai_base_url="https://api.x.ai/v1",
    )


def _use_settings(monkeypatch, *, api_key: str | None):
    monkeypatch.setattr(
        "app.api.v1.finder.get_settings",
        lambda: _settings(api_key=api_key),
    )


# ---------------------------------------------------------------------------
# Normalization and fit
# ---------------------------------------------------------------------------


def test_normalize_label_collapses_case_punctuation_and_whitespace():
    assert normalize_label("  Sr. Software Engineer ") == "sr software engineer"
    assert normalize_label("Software-Engineer") == "software engineer"
    assert role_key("Acme, Inc.", "Sr. Software Engineer") == role_key(
        "Acme Inc", "Sr Software Engineer"
    )


def test_fit_met_when_title_and_every_skill_match():
    assert (
        summarize_fit(
            target_titles="Backend Engineer",
            skills="Python, FastAPI",
            title="Senior Backend Engineer",
            requirements="Python and FastAPI in production",
        )
        == FIT_MET
    )


def test_fit_partial_when_title_matches_but_only_some_skills():
    assert (
        summarize_fit(
            target_titles="Backend Engineer",
            skills="Python, FastAPI, Kubernetes",
            title="Backend Engineer",
            requirements="Python services",
        )
        == FIT_PARTIAL
    )


def test_fit_partial_when_skills_match_but_title_does_not():
    assert (
        summarize_fit(
            target_titles="Data Scientist",
            skills="Python",
            title="Backend Engineer",
            requirements="Python APIs",
        )
        == FIT_PARTIAL
    )


def test_fit_gap_when_nothing_matches():
    assert (
        summarize_fit(
            target_titles="Backend Engineer",
            skills="Python",
            title="Retail Associate",
            requirements="Cash handling",
        )
        == FIT_GAP
    )


def test_fit_gap_when_posting_title_is_blank():
    assert (
        summarize_fit(
            target_titles="Engineer",
            skills="",
            title="",
            requirements="",
        )
        == FIT_GAP
    )


def test_fit_gap_when_profile_is_empty():
    assert (
        summarize_fit(
            target_titles="",
            skills="  ",
            title="Backend Engineer",
            requirements="Python",
        )
        == FIT_GAP
    )


def test_fit_met_on_title_only_profile():
    assert (
        summarize_fit(
            target_titles="Backend Engineer\nData Analyst",
            skills="",
            title="Data Analyst",
            requirements="",
        )
        == FIT_MET
    )


def test_skill_match_respects_word_boundaries():
    assert (
        summarize_fit(
            target_titles="",
            skills="Java",
            title="Frontend Engineer",
            requirements="JavaScript and CSS",
        )
        == FIT_GAP
    )
    assert (
        summarize_fit(
            target_titles="Engineer",
            skills="",
            title="Engineering Manager",
            requirements="",
        )
        == FIT_GAP
    )


# ---------------------------------------------------------------------------
# xAI client — no network
# ---------------------------------------------------------------------------


def test_prompt_keeps_braces_from_the_query():
    prompt = build_prompt(query="role {senior}", target_titles="Eng", skills="Py")
    assert "role {senior}" in prompt
    assert "<<QUERY>>" not in prompt


def test_prompt_clips_long_fields():
    prompt = build_prompt(query="q" * 600, target_titles="t" * 1600, skills="s" * 1600)
    assert "q" * 500 in prompt
    assert "q" * 501 not in prompt
    assert "t" * 1500 in prompt
    assert "t" * 1501 not in prompt


def test_parse_suggestions_drops_invalid_rows_and_empty_pay():
    content = """```json
    {"suggestions": [
      {"title": "Backend Engineer", "company": "Acme", "pay": "N/A",
       "requirements_summary": "Python", "qualification_fit": "met",
       "apply_url": "https://acme.example/apply"},
      {"title": "Nope", "company": "Acme", "apply_url": "javascript:alert(1)"},
      {"title": "", "company": "Acme", "apply_url": "https://acme.example/x"}
    ]}
    ```"""
    parsed = parse_suggestions(content)
    assert len(parsed) == 1
    assert parsed[0].title == "Backend Engineer"
    assert parsed[0].pay is None
    assert parsed[0].apply_url == "https://acme.example/apply"


def test_parse_suggestions_drops_blank_long_and_unsafe_urls():
    rows = [
        "not-a-dict",
        {
            "title": "A" * 501,
            "company": "Acme",
            "apply_url": "https://acme.example/apply",
        },
        {
            "title": "Ok",
            "company": "Acme",
            "apply_url": "https://acme.example/has space",
            "pay": "x" * 300,
        },
    ]
    assert parse_suggestions(json.dumps(rows)) == []
    assert parse_suggestions(json.dumps({"suggestions": "nope"})) == []
    assert (
        parse_suggestions(
            json.dumps(
                {
                    "title": "Ok",
                    "company": "Acme",
                    "apply_url": 12,
                }
            )
        )
        == []
    )
    many = [
        {
            "title": f"Role {i}",
            "company": "Acme",
            "apply_url": f"https://acme.example/{i}",
            "pay": "$1",
        }
        for i in range(7)
    ]
    assert len(parse_suggestions(json.dumps({"jobs": many}))) == 6
    single = parse_suggestions(
        json.dumps(
            {
                "title": "Analyst",
                "company": "Beta",
                "pay": None,
                "apply_url": "http://beta.example/jobs",
            }
        )
    )
    assert len(single) == 1
    assert single[0].pay is None
    assert single[0].requirements_summary == ""


_REAL_CLIENT = httpx.Client


def _patch_client(monkeypatch, handler):
    class _Client:
        def __init__(self, *args, **kwargs):
            self._inner = _REAL_CLIENT(transport=httpx.MockTransport(handler))

        def __enter__(self):
            return self._inner

        def __exit__(self, *exc):
            self._inner.close()
            return False

    monkeypatch.setattr("app.llm.xai_finder.httpx.Client", _Client)


def test_fetch_sends_bearer_token_and_parses_body(monkeypatch):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content.decode())
        payload = {
            "choices": [
                {
                    "message": {
                        "content": [
                            {
                                "text": json.dumps(
                                    {
                                        "suggestions": [
                                            {
                                                "title": "Backend Engineer",
                                                "company": "Acme",
                                                "pay": "$150k",
                                                "requirements_summary": "Python",
                                                "qualification_fit": "met",
                                                "apply_url": "https://acme.example/apply",
                                            }
                                        ]
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }
        return httpx.Response(200, json=payload)

    _patch_client(monkeypatch, handler)
    found = fetch_job_suggestions(
        api_key="test-key",
        model="grok-3",
        base_url="https://api.x.ai/v1",
        query="backend",
        target_titles="Backend Engineer",
        skills="Python",
    )
    assert captured["auth"] == "Bearer test-key"
    assert "test-key" not in json.dumps(captured["body"])
    assert captured["body"]["model"] == "grok-3"
    assert len(found) == 1
    assert found[0].pay == "$150k"


def _fetch(monkeypatch, handler):
    _patch_client(monkeypatch, handler)
    return fetch_job_suggestions(
        api_key="test-key",
        model="grok-3",
        base_url="https://api.x.ai/v1/",
        query="backend",
        target_titles="",
        skills="",
    )


def test_fetch_reports_rejected_key(monkeypatch):
    with pytest.raises(FinderError, match="XAI_API_KEY") as exc:
        _fetch(monkeypatch, lambda request: httpx.Response(401, json={"error": "bad"}))
    assert exc.value.status_code == 502


def test_fetch_reports_rate_limit_and_other_failures(monkeypatch):
    with pytest.raises(FinderError, match="rate limit"):
        _fetch(monkeypatch, lambda request: httpx.Response(429, json={"error": "slow"}))
    with pytest.raises(FinderError, match="could not reach xAI"):
        _fetch(monkeypatch, lambda request: httpx.Response(500, json={"error": "down"}))


def test_fetch_reports_transport_errors(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    with pytest.raises(FinderError, match="could not reach xAI"):
        _fetch(monkeypatch, handler)


def test_fetch_reads_mixed_message_content(monkeypatch):
    payload = json.dumps({"suggestions": []})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": [" ", {"text": payload}]}}]},
        )

    assert _fetch(monkeypatch, handler) == []


def test_fetch_rejects_non_text_content(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})

    with pytest.raises(FinderError, match="unreadable"):
        _fetch(monkeypatch, handler)


def test_fetch_rejects_unreadable_payload(monkeypatch):
    def unreadable(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "nope"}}]})

    with pytest.raises(FinderError, match="unreadable"):
        _fetch(monkeypatch, unreadable)
    with pytest.raises(FinderError, match="unreadable"):
        _fetch(monkeypatch, lambda request: httpx.Response(200, json={"choices": []}))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_profile_round_trip_and_empty_suggestions(client):
    assert client.get("/api/v1/finder/profile").json() == {"target_titles": "", "skills": ""}
    assert client.get("/api/v1/finder/suggestions").json() == []
    saved = client.put(
        "/api/v1/finder/profile",
        json={"target_titles": " Backend Engineer ", "skills": "Python, FastAPI"},
    )
    assert saved.status_code == 200
    assert saved.json() == {"target_titles": "Backend Engineer", "skills": "Python, FastAPI"}
    assert client.get("/api/v1/finder/profile").json() == saved.json()


def test_search_without_api_key_returns_clear_error_and_page_data_still_loads(client, monkeypatch):
    def _boom(**kwargs):
        raise AssertionError("xAI should not be called when the key is missing")

    monkeypatch.setattr("app.services.job_finder.fetch_job_suggestions", _boom)
    _use_settings(monkeypatch, api_key=None)
    client.put("/api/v1/finder/profile", json={"target_titles": "Engineer", "skills": "Python"})

    resp = client.post("/api/v1/finder/search", json={})
    assert resp.status_code == 503
    assert resp.json()["detail"] == MISSING_XAI_KEY_DETAIL
    assert client.get("/api/v1/finder/suggestions").status_code == 200
    assert client.get("/api/v1/finder/profile").status_code == 200


def test_search_ignores_roles_that_normalize_to_blank(client, monkeypatch):
    def _fake(**kwargs):
        return [
            SuggestedJob(
                title="!!!",
                company="@@@",
                pay=None,
                requirements_summary="",
                apply_url="https://x.example/a",
            )
        ]

    monkeypatch.setattr("app.services.job_finder.fetch_job_suggestions", _fake)
    _use_settings(monkeypatch, api_key="test-key")
    resp = client.post("/api/v1/finder/search", json={"query": "anything"})
    assert resp.status_code == 200
    assert resp.json() == {"added": [], "skipped_existing": 0}


def test_profile_and_query_reject_overlong_text(client):
    over_profile = client.put(
        "/api/v1/finder/profile",
        json={"target_titles": "a" * 4001, "skills": "ok"},
    )
    assert over_profile.status_code == 422
    over_query = client.post("/api/v1/finder/search", json={"query": "q" * 501})
    assert over_query.status_code == 422


def test_search_requires_a_query_or_target_titles(client, monkeypatch):
    _use_settings(monkeypatch, api_key="test-key")
    for body in ({"query": None}, {"query": "  "}, {}):
        resp = client.post("/api/v1/finder/search", json=body)
        assert resp.status_code == 422
        assert "target titles" in resp.json()["detail"]


def test_list_omits_roles_that_match_an_application(client, db):
    company = Company(name="Acme, Inc.")
    db.add(company)
    db.flush()
    db.add(Application(company_id=company.id, position="Software Engineer"))
    db.add(
        JobSuggestion(
            title="Software Engineer",
            company_name="Acme Inc",
            pay=None,
            requirements_summary="Python",
            apply_url="https://acme.example/a",
        )
    )
    db.add(
        JobSuggestion(
            title="Data Analyst",
            company_name="Acme Inc",
            pay=None,
            requirements_summary="SQL",
            apply_url="https://acme.example/b",
        )
    )
    db.commit()

    listed = client.get("/api/v1/finder/suggestions").json()
    assert [row["title"] for row in listed] == ["Data Analyst"]
    assert listed[0]["company"] == "Acme Inc"
    assert listed[0]["pay"] is None


def test_search_does_not_store_existing_applications(client, db, monkeypatch):
    company = Company(name="Acme, Inc.")
    db.add(company)
    db.flush()
    db.add(Application(company_id=company.id, position="Sr. Software Engineer"))
    db.commit()

    def _fake(**kwargs):
        assert kwargs["api_key"] == "test-key"
        return [
            SuggestedJob(
                title="Sr Software Engineer",
                company="Acme Inc",
                pay="$10k",
                requirements_summary="Python",
                apply_url="https://acme.example/apply",
            ),
            SuggestedJob(
                title="Data Analyst",
                company="Acme Inc",
                pay="$90k",
                requirements_summary="SQL and spreadsheets",
                apply_url="https://acme.example/analyst",
            ),
        ]

    monkeypatch.setattr("app.services.job_finder.fetch_job_suggestions", _fake)
    _use_settings(monkeypatch, api_key="test-key")
    client.put(
        "/api/v1/finder/profile",
        json={"target_titles": "Data Analyst", "skills": "SQL"},
    )

    resp = client.post("/api/v1/finder/search", json={"query": "analyst"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["skipped_existing"] == 1
    assert [item["title"] for item in body["added"]] == ["Data Analyst"]
    assert body["added"][0]["qualification_fit"] == FIT_MET

    listed = client.get("/api/v1/finder/suggestions").json()
    assert [item["title"] for item in listed] == ["Data Analyst"]
    assert listed[0]["pay"] == "$90k"
    assert listed[0]["apply_url"] == "https://acme.example/analyst"


def test_search_skips_a_suggestion_already_stored(client, db, monkeypatch):
    db.add(
        JobSuggestion(
            title="Data Analyst",
            company_name="Acme",
            pay="$90k",
            requirements_summary="SQL",
            apply_url="https://acme.example/analyst",
        )
    )
    db.commit()

    def _fake(**kwargs):
        return [
            SuggestedJob(
                title="Data Analyst",
                company="Acme",
                pay="$90k",
                requirements_summary="SQL",
                apply_url="https://acme.example/analyst",
            )
        ]

    monkeypatch.setattr("app.services.job_finder.fetch_job_suggestions", _fake)
    _use_settings(monkeypatch, api_key="test-key")
    resp = client.post("/api/v1/finder/search", json={"query": "analyst"})
    assert resp.status_code == 200
    assert resp.json()["added"] == []
    assert resp.json()["skipped_existing"] == 1
    assert len(client.get("/api/v1/finder/suggestions").json()) == 1


def test_fit_on_the_api_follows_the_profile_not_the_posting_alone(client, db):
    db.add(
        JobSuggestion(
            title="Backend Engineer",
            company_name="Acme",
            pay="$140k",
            requirements_summary="Python and FastAPI",
            apply_url="https://acme.example/apply",
        )
    )
    db.commit()
    client.put(
        "/api/v1/finder/profile",
        json={"target_titles": "Backend Engineer", "skills": "Python, FastAPI"},
    )
    assert client.get("/api/v1/finder/suggestions").json()[0]["qualification_fit"] == FIT_MET

    client.put(
        "/api/v1/finder/profile",
        json={"target_titles": "Pastry Chef", "skills": "Lamination"},
    )
    listed = client.get("/api/v1/finder/suggestions").json()
    assert listed[0]["qualification_fit"] == FIT_GAP
    assert listed[0]["pay"] == "$140k"
