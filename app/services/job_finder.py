"""Persist finder suggestions and hide roles that are already applications."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import Application, Company, JobSuggestion, QualificationProfile
from app.llm.errors import FinderError
from app.llm.xai_finder import _clean_pay, _valid_apply_url, fetch_job_suggestions
from app.services.qualification_fit import role_key, summarize_fit

logger = logging.getLogger(__name__)


class SuggestionError(Exception):
    """A create or update that the caller can correct. The message is safe to return."""


EMPTY_SEARCH_DETAIL = "Add target titles to your profile, or enter a search."
MISSING_XAI_KEY_DETAIL = (
    "XAI_API_KEY is not set. Add it to the environment before searching for jobs."
)


def _profile(session: Session) -> QualificationProfile | None:
    return session.query(QualificationProfile).order_by(QualificationProfile.id).first()


def profile_payload(session: Session) -> dict[str, str]:
    row = _profile(session)
    if row is None:
        return {"target_titles": "", "skills": ""}
    return {"target_titles": row.target_titles, "skills": row.skills}


def save_profile(session: Session, *, target_titles: str, skills: str) -> dict[str, str]:
    row = _profile(session)
    if row is None:
        row = QualificationProfile(target_titles=target_titles, skills=skills)
        session.add(row)
    else:
        row.target_titles = target_titles
        row.skills = skills
        row.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(row)
    return {"target_titles": row.target_titles, "skills": row.skills}


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


def _serialize(row: JobSuggestion, profile: dict[str, str]) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "company": row.company_name,
        "pay": row.pay,
        "requirements_summary": row.requirements_summary,
        "qualification_fit": summarize_fit(
            target_titles=profile["target_titles"],
            skills=profile["skills"],
            title=row.title,
            requirements=row.requirements_summary,
        ),
        "apply_url": row.apply_url,
    }


def _stored_suggestions(session: Session) -> list[JobSuggestion]:
    return (
        session.query(JobSuggestion)
        .order_by(JobSuggestion.created_at.desc(), JobSuggestion.id.desc())
        .limit(100)
        .all()
    )


def list_suggestions(session: Session) -> list[dict]:
    """Suggestions whose company and normalized title are not already applications."""
    profile = profile_payload(session)
    applied = _application_keys(session)
    visible = []
    for row in _stored_suggestions(session):
        if role_key(row.company_name, row.title) in applied:
            continue
        visible.append(_serialize(row, profile))
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

    profile = profile_payload(session)
    focus = (query or "").strip() or profile["target_titles"].strip()
    if not focus:
        raise FinderError(EMPTY_SEARCH_DETAIL, status_code=422)

    incoming = fetch_job_suggestions(
        api_key=key,
        model=model,
        base_url=base_url,
        query=focus,
        target_titles=profile["target_titles"],
        skills=profile["skills"],
    )

    applied = _application_keys(session)
    stored = _stored_suggestions(session)
    seen = set(applied) | _suggestion_keys(stored)
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
    profile = profile_payload(session)
    return {
        "added": [_serialize(row, profile) for row in added_rows],
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
    return _serialize(row, profile_payload(session))


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
    return _serialize(row, profile_payload(session))
