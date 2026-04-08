from email.message import EmailMessage
import importlib
import imaplib
from types import SimpleNamespace

import pytest

from app.email_client import client
from app.services.email_service import EmailData


class _FakeMail:
    def __init__(self, raw_by_uid: dict[bytes, bytes]) -> None:
        self._raw_by_uid = raw_by_uid

    def uid(self, command, *args):  # noqa: ANN001
        if command == "search":
            return "OK", [b" ".join(self._raw_by_uid.keys())]
        if command == "fetch":
            uid = args[0]
            raw = self._raw_by_uid[uid]
            return "OK", [(b"RFC822", raw)]
        raise AssertionError(f"Unexpected IMAP command: {command}")

    def close(self) -> None:
        return None

    def logout(self) -> None:
        return None


def _build_email_bytes(
    *,
    message_id: str | None,
    subject: str | None = None,
    sender: str | None = None,
    date: str | None = None,
    body: str | None = None,
) -> bytes:
    msg = EmailMessage()
    if message_id is not None:
        msg["Message-ID"] = message_id
    if subject is not None:
        msg["Subject"] = subject
    if sender is not None:
        msg["From"] = sender
    if date is not None:
        msg["Date"] = date
    if body is not None:
        msg.set_content(body)
    return msg.as_bytes()


def test_fetch_recent_emails_skips_when_message_id_missing(monkeypatch, capsys):
    raw_with_id = _build_email_bytes(message_id="<id-1@example.test>")
    raw_missing_id = _build_email_bytes(message_id=None)
    fake_mail = _FakeMail({b"1": raw_with_id, b"2": raw_missing_id})
    monkeypatch.setattr(client, "_connect_to_inbox", lambda: fake_mail)

    results = client.fetch_recent_emails(limit=10)

    assert len(results) == 1
    assert results[0]["message_id"] == "<id-1@example.test>"
    output = capsys.readouterr().out
    assert "missing required Message-ID header" in output


def test_fetch_recent_emails_includes_soft_required_nullable_keys(monkeypatch):
    raw_with_only_message_id = _build_email_bytes(message_id="<id-2@example.test>")
    fake_mail = _FakeMail({b"1": raw_with_only_message_id})
    monkeypatch.setattr(client, "_connect_to_inbox", lambda: fake_mail)

    results = client.fetch_recent_emails(limit=1)

    assert len(results) == 1
    parsed = results[0]
    assert parsed["message_id"] == "<id-2@example.test>"
    for key in ("subject", "sender", "received_date", "body_text", "raw_headers"):
        assert key in parsed
    assert parsed["subject"] is None
    assert parsed["sender"] is None
    assert parsed["received_date"] is None
    assert parsed["body_text"] is None
    assert isinstance(parsed["raw_headers"], dict)


def test_worker_logs_duplicate_message_id_skip(monkeypatch, capsys):
    import app.config as app_config

    monkeypatch.setattr(
        app_config,
        "get_settings",
        lambda: SimpleNamespace(
            database_url="sqlite:///:memory:",
            llm_provider="ollama",
            email_limit=1,
        ),
    )
    worker_module = importlib.import_module("app.worker")
    worker_module = importlib.reload(worker_module)

    class _FakeSession:
        def commit(self) -> None:
            return None

        def close(self) -> None:
            return None

    class _FakeEmailRepository:
        def __init__(self, session):  # noqa: ANN001
            self.session = session

        def find_by_message_id(self, message_id):  # noqa: ANN001
            return object()

        def create_from_email_data(self, email_data):  # noqa: ANN001
            raise AssertionError("Duplicate should skip create_from_email_data")

    class _FakeCompanyRepository:
        def __init__(self, session):  # noqa: ANN001
            self.session = session

    class _FakeApplicationRepository:
        def __init__(self, session):  # noqa: ANN001
            self.session = session

    class _FakeProcessor:
        def __init__(self, classifier):  # noqa: ANN001
            self.classifier = classifier
            self.email_list = []
            self.application_emails = [
                EmailData(
                    message_id="<dup@example.test>",
                    uid="uid-123",
                    sender="sender@example.test",
                    subject="subject",
                    date=None,
                    body="text",
                )
            ]

        def fetch_emails(self, limit):  # noqa: ANN001
            self.email_list = self.application_emails
            return self.email_list

        def analyze_emails(self):
            return self.application_emails

        def get_high_confidence(self):
            return []

        def get_needs_review(self):
            return []

    monkeypatch.setattr(worker_module, "get_settings", lambda: SimpleNamespace(email_limit=1))
    monkeypatch.setattr(worker_module.models.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(worker_module, "_build_classifier", lambda: object())
    monkeypatch.setattr(worker_module, "EmailProcessor", _FakeProcessor)
    monkeypatch.setattr(worker_module, "SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(worker_module, "EmailRepository", _FakeEmailRepository)
    monkeypatch.setattr(worker_module, "CompanyRepository", _FakeCompanyRepository)
    monkeypatch.setattr(worker_module, "ApplicationRepository", _FakeApplicationRepository)

    worker_module.run()

    output = capsys.readouterr().out
    assert "Duplicate Message-ID — skipping email: <dup@example.test>" in output


def test_fetch_recent_emails_happy_path_full_parse(monkeypatch):
    raw = _build_email_bytes(
        message_id="<full-1@example.test>",
        subject="Offer Update",
        sender="jobs@example.test",
        date="Mon, 01 Jan 2024 10:30:00 +0000",
        body="Thanks for applying.",
    )
    fake_mail = _FakeMail({b"1": raw})
    monkeypatch.setattr(client, "_connect_to_inbox", lambda: fake_mail)

    results = client.fetch_recent_emails(limit=1)

    assert len(results) == 1
    parsed = results[0]
    assert parsed["message_id"] == "<full-1@example.test>"
    assert parsed["subject"] == "Offer Update"
    assert parsed["sender"] == "jobs@example.test"
    assert parsed["received_date"] is not None
    assert parsed["body_text"] == "Thanks for applying."
    assert parsed["raw_headers"]["Message-ID"] == "<full-1@example.test>"


def test_fetch_recent_emails_multiple_valid_emails(monkeypatch):
    raw_by_uid: dict[bytes, bytes] = {}
    expected_ids: set[str] = set()
    for idx in range(1, 6):
        message_id = f"<valid-{idx}@example.test>"
        expected_ids.add(message_id)
        raw_by_uid[str(idx).encode()] = _build_email_bytes(
            message_id=message_id,
            subject=f"Subject {idx}",
            sender=f"sender{idx}@example.test",
            body=f"Body {idx}",
        )

    fake_mail = _FakeMail(raw_by_uid)
    monkeypatch.setattr(client, "_connect_to_inbox", lambda: fake_mail)

    results = client.fetch_recent_emails(limit=10)

    assert len(results) == 5
    returned_ids = {item["message_id"] for item in results}
    assert returned_ids == expected_ids


def test_fetch_recent_emails_respects_limit(monkeypatch):
    raw_by_uid: dict[bytes, bytes] = {}
    for idx in range(1, 6):
        raw_by_uid[str(idx).encode()] = _build_email_bytes(
            message_id=f"<limit-{idx}@example.test>",
            subject=f"Limit {idx}",
            sender=f"limit{idx}@example.test",
            body=f"Body {idx}",
        )

    fake_mail = _FakeMail(raw_by_uid)
    monkeypatch.setattr(client, "_connect_to_inbox", lambda: fake_mail)

    results = client.fetch_recent_emails(limit=3)

    assert len(results) == 3


def test_fetch_recent_emails_malformed_bytes(monkeypatch):
    raw_valid = _build_email_bytes(
        message_id="<valid-after-garbage@example.test>",
        subject="Valid",
        sender="valid@example.test",
        body="This should survive.",
    )
    raw_by_uid = {
        b"1": b"not a real email",
        b"2": raw_valid,
    }
    fake_mail = _FakeMail(raw_by_uid)
    monkeypatch.setattr(client, "_connect_to_inbox", lambda: fake_mail)

    results = client.fetch_recent_emails(limit=10)

    assert len(results) == 1
    assert results[0]["message_id"] == "<valid-after-garbage@example.test>"


def test_fetch_recent_emails_imap_connection_failure(monkeypatch):
    def _raise_connection_error():
        raise imaplib.IMAP4.error("IMAP unavailable")

    monkeypatch.setattr(client, "_connect_to_inbox", _raise_connection_error)

    try:
        results = client.fetch_recent_emails(limit=5)
    except imaplib.IMAP4.error as exc:
        assert "IMAP unavailable" in str(exc)
    else:
        assert results == []


def test_fetch_recent_emails_empty_inbox(monkeypatch):
    fake_mail = _FakeMail({})
    monkeypatch.setattr(client, "_connect_to_inbox", lambda: fake_mail)

    results = client.fetch_recent_emails(limit=10)

    assert results == []


def test_worker_processes_new_email_successfully(monkeypatch):
    import app.config as app_config

    monkeypatch.setattr(
        app_config,
        "get_settings",
        lambda: SimpleNamespace(
            database_url="sqlite:///:memory:",
            llm_provider="ollama",
            email_limit=1,
        ),
    )
    worker_module = importlib.import_module("app.worker")
    worker_module = importlib.reload(worker_module)

    created_records: list[EmailData] = []

    class _FakeSession:
        def commit(self) -> None:
            return None

        def close(self) -> None:
            return None

    class _FakeEmailRepository:
        def __init__(self, session):  # noqa: ANN001
            self.session = session

        def find_by_message_id(self, message_id):  # noqa: ANN001
            return None

        def create_from_email_data(self, email_data):  # noqa: ANN001
            created_records.append(email_data)
            return object()

    class _FakeCompanyRepository:
        def __init__(self, session):  # noqa: ANN001
            self.session = session

    class _FakeApplicationRepository:
        def __init__(self, session):  # noqa: ANN001
            self.session = session

    class _FakeProcessor:
        def __init__(self, classifier):  # noqa: ANN001
            self.classifier = classifier
            self.application_emails = [
                EmailData(
                    message_id="<new@example.test>",
                    uid="uid-200",
                    sender="sender@example.test",
                    subject="subject",
                    date=None,
                    body="text",
                )
            ]
            self.email_list = self.application_emails

        def fetch_emails(self, limit):  # noqa: ANN001
            return self.email_list

        def analyze_emails(self):
            return self.application_emails

        def get_high_confidence(self):
            return []

        def get_needs_review(self):
            return []

    monkeypatch.setattr(worker_module, "get_settings", lambda: SimpleNamespace(email_limit=1))
    monkeypatch.setattr(worker_module.models.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(worker_module, "_build_classifier", lambda: object())
    monkeypatch.setattr(worker_module, "EmailProcessor", _FakeProcessor)
    monkeypatch.setattr(worker_module, "SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(worker_module, "EmailRepository", _FakeEmailRepository)
    monkeypatch.setattr(worker_module, "CompanyRepository", _FakeCompanyRepository)
    monkeypatch.setattr(worker_module, "ApplicationRepository", _FakeApplicationRepository)

    worker_module.run()

    assert len(created_records) == 1
    assert created_records[0].message_id == "<new@example.test>"


def test_worker_handles_zero_application_emails(monkeypatch, capsys):
    import app.config as app_config

    monkeypatch.setattr(
        app_config,
        "get_settings",
        lambda: SimpleNamespace(
            database_url="sqlite:///:memory:",
            llm_provider="ollama",
            email_limit=1,
        ),
    )
    worker_module = importlib.import_module("app.worker")
    worker_module = importlib.reload(worker_module)

    class _FakeProcessor:
        def __init__(self, classifier):  # noqa: ANN001
            self.classifier = classifier
            self.email_list = []
            self.application_emails = []

        def fetch_emails(self, limit):  # noqa: ANN001
            return self.email_list

        def analyze_emails(self):
            return self.application_emails

        def get_high_confidence(self):
            return []

        def get_needs_review(self):
            return []

    def _session_should_not_be_used():
        raise AssertionError("SessionLocal should not be called for zero application emails")

    monkeypatch.setattr(worker_module, "get_settings", lambda: SimpleNamespace(email_limit=1))
    monkeypatch.setattr(worker_module.models.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(worker_module, "_build_classifier", lambda: object())
    monkeypatch.setattr(worker_module, "EmailProcessor", _FakeProcessor)
    monkeypatch.setattr(worker_module, "SessionLocal", _session_should_not_be_used)

    worker_module.run()

    output = capsys.readouterr().out
    assert "No application emails found in this run" in output
