"""
Phase 6 worker tests — exit codes, fast-fail config validation, early-exit paths.

All DB and IMAP interactions are mocked. Tests focus on:
- _validate_config() rejects bad LLM_PROVIDER / missing GROQ_API_KEY
- run() returns EXIT_CONFIG on bad config or DB failure
- run() returns EXIT_NO_SLOT when no WorkerRun slot is available
- run() returns EXIT_OK on a clean (empty) pipeline run
- run() returns EXIT_PIPELINE on unexpected exception and marks run failed
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from app.services.worker_runtime import clear_max_emails_override, set_max_emails_override
from app.worker import (
    EXIT_CONFIG,
    EXIT_NO_SLOT,
    EXIT_OK,
    EXIT_PIPELINE,
    _resolve_uid_cursor,
    _validate_config,
    run,
)


def setup_function():
    clear_max_emails_override()

# ---------------------------------------------------------------------------
# _validate_config unit tests
# ---------------------------------------------------------------------------

def _make_settings(**overrides):
    settings = MagicMock()
    settings.llm_provider = "ollama"
    settings.groq_api_key = None
    for k, v in overrides.items():
        setattr(settings, k, v)
    return settings


def test_validate_config_ollama_ok():
    assert _validate_config(_make_settings(llm_provider="ollama")) is None


def test_validate_config_groq_with_key_ok():
    assert _validate_config(_make_settings(llm_provider="groq", groq_api_key="sk-abc")) is None


def test_validate_config_invalid_provider():
    error = _validate_config(_make_settings(llm_provider="openai"))
    assert error is not None
    assert "LLM_PROVIDER" in error


def test_validate_config_groq_missing_key():
    error = _validate_config(_make_settings(llm_provider="groq", groq_api_key=None))
    assert error is not None
    assert "GROQ_API_KEY" in error


def test_validate_config_groq_empty_key():
    error = _validate_config(_make_settings(llm_provider="groq", groq_api_key=""))
    assert error is not None


@patch("app.worker.get_uid_received_date")
@patch("app.worker.get_latest_uid")
def test_resolve_uid_cursor_keeps_recent_uid(mock_latest_uid, mock_uid_date):
    recent = datetime.now(UTC) - timedelta(days=7)
    mock_uid_date.return_value = recent

    resolved = _resolve_uid_cursor(123, imap_timeout_seconds=30)

    assert resolved == 123
    mock_uid_date.assert_called_once_with(123, timeout=30)
    mock_latest_uid.assert_not_called()


@patch("app.worker.get_uid_received_date")
@patch("app.worker.get_latest_uid")
def test_resolve_uid_cursor_resets_when_tracked_uid_is_stale(mock_latest_uid, mock_uid_date):
    stale = datetime.now(UTC) - timedelta(days=45)
    mock_uid_date.return_value = stale
    mock_latest_uid.return_value = 999

    resolved = _resolve_uid_cursor(123, imap_timeout_seconds=30)

    assert resolved == 999
    mock_uid_date.assert_called_once_with(123, timeout=30)
    mock_latest_uid.assert_called_once_with(timeout=30)


@patch("app.worker.get_uid_received_date")
@patch("app.worker.get_latest_uid")
def test_resolve_uid_cursor_resets_when_tracked_uid_missing(mock_latest_uid, mock_uid_date):
    mock_uid_date.return_value = None
    mock_latest_uid.return_value = 888

    resolved = _resolve_uid_cursor(123, imap_timeout_seconds=30)

    assert resolved == 888
    mock_uid_date.assert_called_once_with(123, timeout=30)
    mock_latest_uid.assert_called_once_with(timeout=30)


# ---------------------------------------------------------------------------
# run() exit code tests
# All tests patch get_settings + DB machinery so nothing real is touched.
# ---------------------------------------------------------------------------

def _good_settings():
    s = MagicMock()
    s.llm_provider = "ollama"
    s.groq_api_key = None
    s.email_limit = 10
    s.max_emails_per_run = 50
    s.stale_run_ttl_minutes = 1440
    s.imap_timeout_seconds = 30
    s.safe_summary.return_value = "provider=ollama imap_server=imap.test"
    return s


@patch("app.worker.get_settings")
def test_run_returns_exit_config_on_bad_provider(mock_gs):
    s = _good_settings()
    s.llm_provider = "invalid"
    mock_gs.return_value = s
    assert run() == EXIT_CONFIG


@patch("app.worker.get_settings")
def test_run_returns_exit_config_when_settings_raise(mock_gs):
    mock_gs.side_effect = RuntimeError("env var missing")
    assert run() == EXIT_CONFIG


@patch("app.worker.get_settings")
def test_run_returns_exit_config_on_db_failure(mock_gs):
    mock_gs.return_value = _good_settings()
    with patch("app.worker.models") as mock_models:
        mock_models.Base.metadata.create_all.side_effect = Exception("DB down")
        assert run() == EXIT_CONFIG


def _patch_worker_infra(settings=None, *, worker_run=None, create_run=True):
    """Return a dict of patches for a minimal passing run() invocation."""
    if settings is None:
        settings = _good_settings()

    mock_run_obj = MagicMock()
    mock_run_obj.id = 42

    mock_run_repo = MagicMock()
    mock_run_repo.reconcile_stale_worker_runs.return_value = None
    mock_run_repo.get_latest_run.return_value = None
    if create_run:
        mock_run_repo.try_create_queued_run.return_value = mock_run_obj
        mock_run_repo.claim_if_queued.return_value = mock_run_obj
    else:
        mock_run_repo.try_create_queued_run.return_value = None

    mock_session = MagicMock()

    mock_processor = MagicMock()
    mock_processor.email_list = []
    mock_processor.application_emails = []
    mock_processor.get_high_confidence.return_value = []
    mock_processor.get_needs_review.return_value = []

    return {
        "settings": settings,
        "run_repo": mock_run_repo,
        "session": mock_session,
        "processor": mock_processor,
        "run_obj": mock_run_obj,
    }


@patch("app.worker.get_settings")
def test_run_returns_exit_no_slot_when_no_run_available(mock_gs):
    infra = _patch_worker_infra(create_run=False)
    mock_gs.return_value = infra["settings"]

    with patch("app.worker.models"), \
         patch("app.worker.SessionLocal", return_value=infra["session"]), \
         patch("app.worker.WorkerRunRepository", return_value=infra["run_repo"]):
        result = run()

    assert result == EXIT_NO_SLOT


@patch("app.worker.get_settings")
def test_run_returns_exit_ok_on_empty_inbox(mock_gs):
    infra = _patch_worker_infra()
    mock_gs.return_value = infra["settings"]

    with patch("app.worker.models"), \
         patch("app.worker.SessionLocal", return_value=infra["session"]), \
         patch("app.worker.WorkerRunRepository", return_value=infra["run_repo"]), \
         patch("app.worker.EmailRepository"), \
         patch("app.worker.CompanyRepository"), \
         patch("app.worker.ApplicationRepository"), \
         patch("app.worker.AnalysisRepository"), \
         patch("app.worker.build_classifier"), \
         patch("app.worker.EmailProcessor", return_value=infra["processor"]):
        result = run()

    assert result == EXIT_OK
    infra["run_repo"].complete.assert_called_once()


@patch("app.worker.get_settings")
def test_run_returns_exit_pipeline_on_unexpected_exception(mock_gs):
    infra = _patch_worker_infra()
    mock_gs.return_value = infra["settings"]

    infra["run_repo"].claim_if_queued.side_effect = RuntimeError("unexpected boom")

    with patch("app.worker.models"), \
         patch("app.worker.SessionLocal", return_value=infra["session"]), \
         patch("app.worker.WorkerRunRepository", return_value=infra["run_repo"]):
        result = run()

    assert result == EXIT_PIPELINE


@patch("app.worker.get_settings")
def test_run_api_triggered_returns_exit_no_slot_when_run_not_claimable(mock_gs):
    """When worker_run_id is passed but claim fails, return EXIT_NO_SLOT."""
    infra = _patch_worker_infra()
    mock_gs.return_value = infra["settings"]

    infra["run_repo"].get_by_id.return_value = infra["run_obj"]
    infra["run_repo"].claim_if_queued.return_value = None

    with patch("app.worker.models"), \
         patch("app.worker.SessionLocal", return_value=infra["session"]), \
         patch("app.worker.WorkerRunRepository", return_value=infra["run_repo"]):
        result = run(worker_run_id=42)

    assert result == EXIT_NO_SLOT


@patch("app.worker.get_settings")
def test_run_api_triggered_returns_exit_pipeline_when_run_not_found(mock_gs):
    """When worker_run_id is passed but the row is missing, return EXIT_PIPELINE."""
    infra = _patch_worker_infra()
    mock_gs.return_value = infra["settings"]

    infra["run_repo"].get_by_id.return_value = None

    with patch("app.worker.models"), \
         patch("app.worker.SessionLocal", return_value=infra["session"]), \
         patch("app.worker.WorkerRunRepository", return_value=infra["run_repo"]):
        result = run(worker_run_id=99)

    assert result == EXIT_PIPELINE


@patch("app.worker.get_settings")
def test_run_uses_runtime_email_limit_override(mock_gs):
    infra = _patch_worker_infra()
    mock_gs.return_value = infra["settings"]
    infra["run_repo"].get_latest_run.return_value = None
    set_max_emails_override(7)

    with patch("app.worker.models"), \
         patch("app.worker.SessionLocal", return_value=infra["session"]), \
         patch("app.worker.WorkerRunRepository", return_value=infra["run_repo"]), \
         patch("app.worker.EmailRepository"), \
         patch("app.worker.CompanyRepository"), \
         patch("app.worker.ApplicationRepository"), \
         patch("app.worker.AnalysisRepository"), \
         patch("app.worker.build_classifier"), \
         patch("app.worker.EmailProcessor", return_value=infra["processor"]):
        result = run()

    assert result == EXIT_OK
    infra["processor"].fetch_emails.assert_called_once_with(7, since_uid=1)


@patch("app.worker.get_settings")
def test_api_email_limit_endpoint_flows_through_to_worker(mock_gs):
    """End-to-end: POST /jobs/email-limit sets override, then run() uses it."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.v1.router import api_router

    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    client = TestClient(app)

    resp = client.post("/api/v1/jobs/email-limit", json={"max_emails_per_run": 15})
    assert resp.status_code == 200
    assert resp.json()["max_emails_per_run"] == 15

    infra = _patch_worker_infra()
    mock_gs.return_value = infra["settings"]
    infra["run_repo"].get_latest_run.return_value = None

    with patch("app.worker.models"), \
         patch("app.worker.SessionLocal", return_value=infra["session"]), \
         patch("app.worker.WorkerRunRepository", return_value=infra["run_repo"]), \
         patch("app.worker.EmailRepository"), \
         patch("app.worker.CompanyRepository"), \
         patch("app.worker.ApplicationRepository"), \
         patch("app.worker.AnalysisRepository"), \
         patch("app.worker.build_classifier"), \
         patch("app.worker.EmailProcessor", return_value=infra["processor"]):
        result = run()

    assert result == EXIT_OK
    infra["processor"].fetch_emails.assert_called_once_with(15, since_uid=1)
