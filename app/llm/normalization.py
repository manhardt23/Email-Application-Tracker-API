import json
import re
from typing import Any

from app.llm.base import EmailClassification
from app.llm.errors import LLMResponseError

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(content: str) -> dict[str, Any]:
    match = _JSON_BLOCK_RE.search(content)
    if not match:
        raise LLMResponseError("No JSON object found in provider response.")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMResponseError(f"Invalid JSON in provider response: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMResponseError("Provider response JSON is not an object.")
    return data


_NULL_TEXT = {"", "null", "none", "n/a", "na", "undefined"}
_CANONICAL_STAGES = {"applied", "rejected", "interview", "offer", "assessment", "other"}


def clean_optional_text(value: Any) -> str | None:
    """Drop placeholder company/position values the model emits as strings."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _NULL_TEXT:
        return None
    return text


def canonicalize_stage(stage: Any) -> str | None:
    """Map free-text stages onto the stages the dashboard and API understand.

    Unrecognized values become None so a new application stays at the
    ``applied`` default instead of a one-off label that metrics ignore.
    """
    if stage is None:
        return None
    text = str(stage).strip().lower()
    if text in _NULL_TEXT:
        return None
    if text in _CANONICAL_STAGES:
        return text
    if re.search(
        r"reject|declin|not selected|not moving forward|unsuccessful|other candidates",
        text,
    ):
        return "rejected"
    if text in {"screening", "phone screen", "onsite", "on-site", "on site"}:
        return "interview"
    if re.search(r"\boffer\b", text):
        return "offer"
    if re.search(r"assess|take-home|take home|coding challenge|hackerrank|codility", text):
        return "assessment"
    if re.search(r"interview|phone screen|on-?site|screening", text):
        return "interview"
    if re.search(r"\bappl|\breceived\b|\bsubmitted\b|under review", text):
        return "applied"
    return None


def normalize_classification(data: dict[str, Any]) -> EmailClassification:
    confidence = str(data.get("confidence", "low")).lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
    raw = data.get("is_application", False)
    if isinstance(raw, bool):
        is_application = raw
    elif isinstance(raw, str):
        is_application = raw.strip().lower() == "true"
    else:
        is_application = False

    return EmailClassification(
        is_application=is_application,
        company=clean_optional_text(data.get("company")),
        position=clean_optional_text(data.get("position")),
        stage=canonicalize_stage(data.get("stage")),
        confidence=confidence,
    )
