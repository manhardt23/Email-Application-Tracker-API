"""Persist finder suggestions and hide roles that are already applications."""

from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.db.models import Application, Company, JobSuggestion
from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository
from app.llm.errors import FinderError
from app.llm.xai_finder import _clean_pay, _valid_apply_url, fetch_job_suggestions

logger = logging.getLogger(__name__)


class SuggestionError(Exception):
    """A create, update, or dismiss that the caller can correct. The message is safe to return."""


EMPTY_SEARCH_DETAIL = "Enter a search."
MISSING_XAI_KEY_DETAIL = (
    "XAI_API_KEY is not set. Add it to the environment before searching for jobs."
)


def normalize_label(value: str | None) -> str:
    """Case-fold and collapse punctuation and whitespace to single spaces."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def role_key(company: str | None, title: str | None) -> tuple[str, str]:
    return normalize_label(company), normalize_label(title)


def _application_keys(session: Session) -> set[tuple[str, str]]:
    rows = session.query(Company.name, Application.position).join(Company).all()
    keys = set()
    for name, position in rows:
        key = role_key(name, position)
        if key != ("", ""):
            keys.add(key)
    return keys


def _suggestion_keys(rows: list[JobSuggestion]) -> set[tuple[str, str]]:
    keys = set()
    for row in rows:
        key = role_key(row.company_name, row.title)
        if key != ("", ""):
            keys.add(key)
    return keys


def _serialize(row: JobSuggestion) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "company": row.company_name,
        "pay": row.pay,
        "requirements_summary": row.requirements_summary,
        "apply_url": row.apply_url,
    }


def _stored_suggestions(session: Session) -> list[JobSuggestion]:
    return (
        session.query(JobSuggestion)
        .filter(JobSuggestion.dismissed.is_(False))
        .order_by(JobSuggestion.created_at.desc(), JobSuggestion.id.desc())
        .limit(100)
        .all()
    )


def _dismissed_keys(session: Session) -> set[tuple[str, str]]:
    rows = (
        session.query(JobSuggestion.company_name, JobSuggestion.title)
        .filter(JobSuggestion.dismissed.is_(True))
        .all()
    )
    keys = set()
    for name, title in rows:
        key = role_key(name, title)
        if key != ("", ""):
            keys.add(key)
    return keys


def list_suggestions(session: Session) -> list[dict]:
    """Suggestions whose company and normalized title are not already applications."""
    applied = _application_keys(session)
    visible = []
    for row in _stored_suggestions(session):
        if role_key(row.company_name, row.title) in applied:
            continue
        visible.append(_serialize(row))
    return visible


def search_jobs(
    session: Session,
    *,
    query: str | None,
    api_key: str | None,
    model: str,
    base_url: str,
) -> dict:
    key = (api_key or "").strip()
    if not key:
        raise FinderError(MISSING_XAI_KEY_DETAIL, status_code=503)

    focus = (query or "").strip()
    if not focus:
        raise FinderError(EMPTY_SEARCH_DETAIL, status_code=422)

    incoming = fetch_job_suggestions(
        api_key=key,
        model=model,
        base_url=base_url,
        query=focus,
    )

    applied = _application_keys(session)
    stored = _stored_suggestions(session)
    seen = set(applied) | _suggestion_keys(stored) | _dismissed_keys(session)
    added_rows: list[JobSuggestion] = []
    skipped_existing = 0

    for job in incoming:
        key_pair = role_key(job.company, job.title)
        if key_pair == ("", ""):
            continue
        if key_pair in seen:
            skipped_existing += 1
            continue
        row = JobSuggestion(
            title=job.title,
            company_name=job.company,
            pay=job.pay,
            requirements_summary=job.requirements_summary,
            apply_url=job.apply_url,
        )
        session.add(row)
        added_rows.append(row)
        seen.add(key_pair)

    session.commit()
    for row in added_rows:
        session.refresh(row)

    logger.info("finder search added=%s skipped_existing=%s", len(added_rows), skipped_existing)
    return {
        "added": [_serialize(row) for row in added_rows],
        "skipped_existing": skipped_existing,
    }


def _label(value: str, field: str, limit: int) -> str:
    text = value.strip()
    if not text:
        raise SuggestionError(f"{field} is required")
    if len(text) > limit:
        raise SuggestionError(f"{field} must be {limit} characters or fewer")
    return text


def _summary(value: str) -> str:
    text = value.strip()
    if len(text) > 2000:
        raise SuggestionError("requirements_summary must be 2000 characters or fewer")
    return text


def _apply_url(value: str) -> str:
    url = _valid_apply_url(value)
    if url is None:
        raise SuggestionError("apply_url must be an http or https link")
    return url


def _conflict(
    session: Session, company: str, title: str, *, exclude_id: int | None = None
) -> str | None:
    key = role_key(company, title)
    if key in _application_keys(session):
        return "That company and title is already an application"
    for row in session.query(JobSuggestion).all():
        if exclude_id is not None and row.id == exclude_id:
            continue
        if role_key(row.company_name, row.title) == key:
            return "A suggestion already exists for that company and title"
    return None


def create_suggestion(
    session: Session,
    *,
    title: str,
    company: str,
    apply_url: str,
    pay: str | None = None,
    requirements_summary: str = "",
) -> dict:
    """Store one suggestion. Does not call xAI and does not save a job-site login."""
    clean_title = _label(title, "title", 500)
    clean_company = _label(company, "company", 255)
    conflict = _conflict(session, clean_company, clean_title)
    if conflict:
        raise SuggestionError(conflict)
    row = JobSuggestion(
        title=clean_title,
        company_name=clean_company,
        pay=_clean_pay(pay),
        requirements_summary=_summary(requirements_summary),
        apply_url=_apply_url(apply_url),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _serialize(row)


def update_suggestion(session: Session, suggestion_id: int, changes: dict) -> dict:
    """Update fields on one suggestion. An empty change set is rejected."""
    if not changes:
        raise SuggestionError("Provide a field to update")
    unknown = set(changes) - {"title", "company", "pay", "requirements_summary", "apply_url"}
    if unknown:
        raise SuggestionError("Unknown suggestion fields")

    row = session.query(JobSuggestion).filter(JobSuggestion.id == suggestion_id).first()
    if row is None:
        raise SuggestionError("Suggestion not found")

    title = _label(str(changes["title"]), "title", 500) if "title" in changes else row.title
    if "company" in changes:
        company = _label(str(changes["company"]), "company", 255)
    else:
        company = row.company_name
    if role_key(company, title) != role_key(row.company_name, row.title):
        conflict = _conflict(session, company, title, exclude_id=row.id)
        if conflict:
            raise SuggestionError(conflict)

    row.title = title
    row.company_name = company
    if "pay" in changes:
        raw_pay = changes["pay"]
        row.pay = _clean_pay(None if raw_pay is None else str(raw_pay))
    if "requirements_summary" in changes:
        row.requirements_summary = _summary(str(changes["requirements_summary"] or ""))
    if "apply_url" in changes:
        row.apply_url = _apply_url(str(changes["apply_url"]))

    session.commit()
    session.refresh(row)
    return _serialize(row)


def dismiss_suggestion(session: Session, suggestion_id: int) -> dict:
    """Hide one suggestion. The row stays stored and no application is created."""
    row = session.query(JobSuggestion).filter(JobSuggestion.id == suggestion_id).first()
    if row is None:
        raise SuggestionError("Suggestion not found")
    row.dismissed = True
    session.commit()
    session.refresh(row)
    return {"id": row.id, "dismissed": True}


def _posting_notes(apply_url: str, pay: str | None) -> str:
    """Apply URL on its own line, plus the pay line only when pay is present."""
    lines = [apply_url.strip()]
    pay_line = (pay or "").strip()
    if pay_line:
        lines.append(pay_line)
    return "\n".join(lines)


def apply_suggestion(session: Session, suggestion_id: int) -> dict:
    """Record the suggestion as an application. Does not dismiss the suggestion.

    A later list hides the card because the company and title match an
    application. An existing application is returned unchanged.
    """
    row = session.query(JobSuggestion).filter(JobSuggestion.id == suggestion_id).first()
    if row is None:
        raise SuggestionError("Suggestion not found")

    company = CompanyRepository(session).find_or_create(row.company_name)
    applications = ApplicationRepository(session)
    existing = applications.find_by_company_and_position(company.id, row.title)
    application = applications.find_or_create(company.id, row.title)
    created = existing is None
    if created:
        application.notes = _posting_notes(row.apply_url, row.pay)

    session.commit()
    session.refresh(application)
    return {
        "application_id": application.id,
        "company": company.name,
        "position": application.position,
        "stage": application.stage,
        "created": created,
    }
