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


def normalize_classification(data: dict[str, Any]) -> EmailClassification:
    stage = data.get("stage")
    confidence = str(data.get("confidence", "low")).lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"

    return EmailClassification(
        is_application=bool(data.get("is_application", False)),
        company=data.get("company"),
        position=data.get("position"),
        stage=stage if stage is None else str(stage),
        confidence=confidence,
    )
