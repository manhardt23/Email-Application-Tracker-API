"""MCP tool implementations. Each one opens its own DB session."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime

from mcp.server.fastmcp.exceptions import ToolError
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.repositories.application_repo import ApplicationRepository
from app.services.job_finder import (
    SuggestionError,
    create_suggestion,
    list_suggestions,
    profile_payload,
    save_profile,
    update_suggestion,
)

session_factory: Callable[[], Session] = SessionLocal

_PROFILE_LIMIT = 4000


@contextmanager
def session_scope():
    db = session_factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _profile_text(value: str, field: str) -> str:
    text = value.strip()
    if len(text) > _PROFILE_LIMIT:
        raise ToolError(f"{field} must be {_PROFILE_LIMIT} characters or fewer")
    return text


def list_applications(limit: int = 1000, offset: int = 0) -> dict:
    if limit < 1 or limit > 1000:
        raise ToolError("limit must be between 1 and 1000")
    if offset < 0:
        raise ToolError("offset must be 0 or greater")
    with session_scope() as db:
        items, total = ApplicationRepository(db).search(limit=limit, offset=offset)
        return {
            "items": [
                {
                    "id": row.id,
                    "company": row.company.name if row.company is not None else "",
                    "title": row.position,
                    "stage": row.stage,
                }
                for row in items
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


def get_application(application_id: int) -> dict:
    with session_scope() as db:
        row = ApplicationRepository(db).get_by_id(application_id)
        if row is None:
            raise ToolError("Application not found")
        return {
            "id": row.id,
            "company": row.company.name if row.company is not None else "",
            "title": row.position,
            "stage": row.stage,
            "notes": row.notes,
            "applied_date": _iso(row.applied_date),
            "last_updated": _iso(row.last_updated),
        }


def list_job_suggestions() -> dict:
    with session_scope() as db:
        items = list_suggestions(db)
        return {"items": items, "total": len(items)}


def create_job_suggestion(
    title: str,
    company: str,
    apply_url: str,
    pay: str | None = None,
    requirements_summary: str = "",
) -> dict:
    with session_scope() as db:
        try:
            return create_suggestion(
                db,
                title=title,
                company=company,
                apply_url=apply_url,
                pay=pay,
                requirements_summary=requirements_summary,
            )
        except SuggestionError as exc:
            raise ToolError(str(exc)) from exc


def update_job_suggestion(
    suggestion_id: int,
    title: str | None = None,
    company: str | None = None,
    pay: str | None = None,
    requirements_summary: str | None = None,
    apply_url: str | None = None,
) -> dict:
    changes: dict = {}
    if title is not None:
        changes["title"] = title
    if company is not None:
        changes["company"] = company
    if pay is not None:
        changes["pay"] = pay
    if requirements_summary is not None:
        changes["requirements_summary"] = requirements_summary
    if apply_url is not None:
        changes["apply_url"] = apply_url
    with session_scope() as db:
        try:
            return update_suggestion(db, suggestion_id, changes)
        except SuggestionError as exc:
            raise ToolError(str(exc)) from exc


def get_job_finder_profile() -> dict:
    with session_scope() as db:
        return profile_payload(db)


def update_job_finder_profile(target_titles: str = "", skills: str = "") -> dict:
    titles = _profile_text(target_titles, "target_titles")
    skill_text = _profile_text(skills, "skills")
    with session_scope() as db:
        return save_profile(db, target_titles=titles, skills=skill_text)
