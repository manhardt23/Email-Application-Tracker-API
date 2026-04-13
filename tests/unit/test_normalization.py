"""
Unit tests for app.llm.normalization.

Covers: extract_json_object, normalize_classification — including edge
cases for malformed input, confidence clamping, and string is_application.
"""
import pytest

from app.llm.errors import LLMResponseError
from app.llm.normalization import extract_json_object, normalize_classification


class TestExtractJsonObject:
    def test_extracts_plain_object(self):
        data = extract_json_object('{"key": "value"}')
        assert data == {"key": "value"}

    def test_extracts_object_from_surrounding_text(self):
        data = extract_json_object('Some text before {"a": 1} and after')
        assert data["a"] == 1

    def test_raises_when_no_json(self):
        with pytest.raises(LLMResponseError, match="No JSON object"):
            extract_json_object("plain text with no json")

    def test_raises_on_invalid_json(self):
        with pytest.raises(LLMResponseError, match="Invalid JSON"):
            extract_json_object("{not valid json}")

    def test_nested_object_parses_successfully(self):
        # Verify deeply nested content doesn't crash extraction
        data = extract_json_object('{"x": [1, 2], "y": {"z": true}}')
        assert data["x"] == [1, 2]


class TestNormalizeClassification:
    def test_full_classification(self):
        result = normalize_classification({
            "is_application": True,
            "company": "Acme",
            "position": "SWE",
            "stage": "interview",
            "confidence": "high",
        })
        assert result.is_application is True
        assert result.company == "Acme"
        assert result.stage == "interview"
        assert result.confidence == "high"

    def test_string_true_is_application(self):
        result = normalize_classification({
            "is_application": "true",
            "confidence": "medium",
        })
        assert result.is_application is True

    def test_string_false_is_application(self):
        result = normalize_classification({
            "is_application": "false",
            "confidence": "high",
        })
        assert result.is_application is False

    def test_non_bool_non_string_defaults_false(self):
        result = normalize_classification({"is_application": 1, "confidence": "high"})
        assert result.is_application is False

    def test_unknown_confidence_clamped_to_low(self):
        result = normalize_classification({"is_application": False, "confidence": "unknown"})
        assert result.confidence == "low"

    def test_missing_confidence_defaults_to_low(self):
        result = normalize_classification({"is_application": False})
        assert result.confidence == "low"

    def test_none_stage_preserved(self):
        result = normalize_classification(
            {"is_application": False, "stage": None, "confidence": "high"}
        )
        assert result.stage is None

    def test_numeric_stage_cast_to_string(self):
        result = normalize_classification(
            {"is_application": True, "stage": 3, "confidence": "medium"}
        )
        assert result.stage == "3"
