"""xAI Grok job finder.

Separate from the Groq email classifier in ``groq_adapter``. Reads ``XAI_API_KEY``
at call time. This module does not talk to Groq.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.llm.errors import FinderError
from app.llm.normalization import extract_json_object

logger = logging.getLogger(__name__)

_PROMPT = """\
Suggest open job postings the user could apply to themselves.

Search focus:
<<QUERY>>

Return ONLY valid JSON with no explanation:
{
  "suggestions": [
    {
      "title": "string",
      "company": "string",
      "pay": "short pay string or null if the posting does not list pay",
      "requirements_summary": "one sentence of requirements",
      "apply_url": "https link to the company application page"
    }
  ]
}

Rules:
- At most 6 suggestions.
- Every apply_url must be an http or https link on the company's own application page.
- Use null for pay when the posting does not list it.
- Do not score the posting against a profile, target titles, or skills.
- Skip roles you cannot ground with a real apply URL.
"""

_EMPTY_PAY = {"", "n/a", "na", "none", "null", "unknown", "not listed", "not specified", "-"}
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


@dataclass(frozen=True)
class SuggestedJob:
    title: str
    company: str
    pay: str | None
    requirements_summary: str
    apply_url: str


def _clip(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:limit]


def build_prompt(*, query: str) -> str:
    return _PROMPT.replace("<<QUERY>>", _clip(query, 500))


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text") or part.get("content") or ""
                parts.append(str(text))
        return "".join(parts)
    return ""


def _load_payload(content: str) -> Any:
    text = _FENCE.sub("", content.strip()).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return extract_json_object(text)


def _items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("suggestions", "jobs", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        if "title" in payload and "company" in payload:
            return [payload]
    return []


def _clean_pay(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.casefold() in _EMPTY_PAY:
        return None
    return text[:255]


def _valid_apply_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    url = value.strip()
    if len(url) > 2000 or any(ch.isspace() for ch in url):
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return url


def parse_suggestions(content: str) -> list[SuggestedJob]:
    """Turn model output into suggestions. Invalid rows are dropped."""
    try:
        payload = _load_payload(content)
    except Exception as exc:  # noqa: BLE001 — LLMResponseError and JSON errors
        raise FinderError("Job search returned an unreadable response.") from exc

    suggestions: list[SuggestedJob] = []
    for item in _items(payload):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        company = str(item.get("company") or "").strip()
        apply_url = _valid_apply_url(item.get("apply_url"))
        if not title or not company or apply_url is None:
            continue
        if len(title) > 500 or len(company) > 255:
            continue
        summary = str(item.get("requirements_summary") or "").strip()[:2000]
        suggestions.append(
            SuggestedJob(
                title=title,
                company=company,
                pay=_clean_pay(item.get("pay")),
                requirements_summary=summary,
                apply_url=apply_url,
            )
        )
        if len(suggestions) >= 6:
            break
    return suggestions


def fetch_job_suggestions(
    *,
    api_key: str,
    model: str,
    base_url: str,
    query: str,
) -> list[SuggestedJob]:
    """Call xAI chat completions and return parsed suggestions."""
    url = base_url.rstrip("/") + "/chat/completions"
    prompt = build_prompt(query=query)
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": 0,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
    except httpx.HTTPError as exc:
        logger.warning("xAI finder request failed: %s", type(exc).__name__)
        raise FinderError("Job search failed. The finder could not reach xAI.") from exc

    if response.status_code == 401:
        logger.warning("xAI finder rejected the API key")
        raise FinderError("xAI rejected XAI_API_KEY. Check the key and try again.")
    if response.status_code == 429:
        logger.warning("xAI finder rate limited")
        raise FinderError("xAI rate limit reached. Try again shortly.")
    if response.status_code >= 400:
        logger.warning("xAI finder request failed status=%s", response.status_code)
        raise FinderError("Job search failed. The finder could not reach xAI.")

    try:
        body = response.json()
        message = body["choices"][0]["message"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise FinderError("Job search returned an unreadable response.") from exc

    return parse_suggestions(_message_text(message))
