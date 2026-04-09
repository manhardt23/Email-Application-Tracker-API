import sys
from types import SimpleNamespace

import pytest

from app.llm.base import EmailClassification
from app.llm.errors import LLMResponseError
from app.llm.factory import build_classifier
from app.llm.groq_adapter import GroqAdapter
from app.llm.ollama_adapter import OllamaAdapter
from app.services.email_service import EmailData


def test_build_classifier_routes_to_ollama(monkeypatch):
    fake_module = SimpleNamespace(OllamaAdapter=lambda: "ollama-classifier")
    monkeypatch.setitem(sys.modules, "app.llm.ollama_adapter", fake_module)
    settings = SimpleNamespace(llm_provider="ollama", groq_api_key=None)

    classifier = build_classifier(settings)

    assert classifier == "ollama-classifier"


def test_build_classifier_routes_to_groq(monkeypatch):
    fake_module = SimpleNamespace(GroqAdapter=lambda api_key: ("groq-classifier", api_key))
    monkeypatch.setitem(sys.modules, "app.llm.groq_adapter", fake_module)
    settings = SimpleNamespace(llm_provider="groq", groq_api_key="test-key")

    classifier = build_classifier(settings)

    assert classifier == ("groq-classifier", "test-key")


def test_build_classifier_rejects_invalid_provider():
    settings = SimpleNamespace(llm_provider="bad-provider", groq_api_key=None)

    with pytest.raises(ValueError, match="Invalid LLM_PROVIDER"):
        build_classifier(settings)


def test_groq_adapter_normalizes_response(monkeypatch):
    fake_groq = SimpleNamespace(Groq=lambda api_key: SimpleNamespace())
    monkeypatch.setitem(sys.modules, "groq", fake_groq)
    adapter = GroqAdapter(api_key="test-key")
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"is_application": true, "company": "Acme", "position": "SWE", "stage": "interview", "confidence": "high"}'
                )
            )
        ]
    )
    adapter.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: response)
        )
    )

    result = adapter.classify_email("jobs@example.com", "Interview", "Body")

    assert result is not None
    assert result.is_application is True
    assert result.company == "Acme"
    assert result.position == "SWE"
    assert result.stage == "interview"
    assert result.confidence == "high"


def test_groq_adapter_raises_on_invalid_json(monkeypatch):
    fake_groq = SimpleNamespace(Groq=lambda api_key: SimpleNamespace())
    monkeypatch.setitem(sys.modules, "groq", fake_groq)
    adapter = GroqAdapter(api_key="test-key")
    bad = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))]
    )
    adapter.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: bad))
    )

    with pytest.raises(LLMResponseError):
        adapter.classify_email("jobs@example.com", "Subject", "Body")


def test_ollama_adapter_normalizes_response(monkeypatch):
    monkeypatch.setattr(
        "app.llm.ollama_adapter.ollama.chat",
        lambda **kwargs: {
            "message": {
                "content": '{"is_application": false, "company": null, "position": null, "stage": null, "confidence": "medium"}'
            }
        },
    )
    adapter = OllamaAdapter()

    result = adapter.classify_email("sender@example.com", "Subject", "Body")

    assert result is not None
    assert result.is_application is False
    assert result.stage is None
    assert result.confidence == "medium"


def test_ollama_adapter_raises_on_invalid_json(monkeypatch):
    monkeypatch.setattr(
        "app.llm.ollama_adapter.ollama.chat",
        lambda **kwargs: {"message": {"content": "oops"}},
    )
    adapter = OllamaAdapter()

    with pytest.raises(LLMResponseError):
        adapter.classify_email("sender@example.com", "Subject", "Body")


def test_pipeline_skips_llm_when_quick_filter_fails(monkeypatch):
    calls = {"count": 0}

    class DummyClassifier:
        provider_name = "ollama"

        def classify_email(self, sender: str, subject: str, body: str):
            calls["count"] += 1
            return EmailClassification(is_application=True, confidence="high")

    monkeypatch.setattr("app.services.email_service.quick_filter", lambda *args: False)
    email = EmailData(
        message_id="<m1@example.com>",
        uid="1",
        sender="nope@example.com",
        subject="newsletter",
        date=None,
        body="not job related",
    )

    is_application = email.classify(DummyClassifier())

    assert is_application is False
    assert calls["count"] == 0


def test_pipeline_classifies_with_provider_and_sets_fields(monkeypatch):
    class DummyClassifier:
        provider_name = "groq"

        def classify_email(self, sender: str, subject: str, body: str):
            return EmailClassification(
                is_application=True,
                company="Acme",
                position="Backend Engineer",
                stage="applied",
                confidence="high",
            )

    monkeypatch.setattr("app.services.email_service.quick_filter", lambda *args: True)
    email = EmailData(
        message_id="<m2@example.com>",
        uid="2",
        sender="jobs@example.com",
        subject="Thanks for applying",
        date=None,
        body="application received",
    )

    is_application = email.classify(DummyClassifier())

    assert is_application is True
    assert email.company == "Acme"
    assert email.position == "Backend Engineer"
    assert email.stage == "applied"
    assert email.confidence == "high"
