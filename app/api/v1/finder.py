"""Job finder: stored suggestions and the xAI search."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth.dependencies import AdminUser, get_db
from app.config import get_settings
from app.llm.errors import FinderError
from app.middleware.rate_limit import EXPENSIVE_LIMIT, limiter
from app.services.job_finder import (
    SuggestionError,
    dismiss_suggestion,
    list_suggestions,
    search_jobs,
)

router = APIRouter()

DbDep = Annotated[Session, Depends(get_db)]


class SearchRequest(BaseModel):
    query: str | None = None

    @field_validator("query")
    @classmethod
    def _bounded_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if len(text) > 500:
            raise ValueError("query must be 500 characters or fewer")
        return text


@router.get("/suggestions")
def get_suggestions(db: DbDep, _user: AdminUser):
    return list_suggestions(db)


@router.post("/suggestions/{suggestion_id}/dismiss")
def dismiss_suggestion_from_list(suggestion_id: int, db: DbDep, _user: AdminUser):
    """Hide a suggestion. It leaves the list and is not created as an application."""
    try:
        return dismiss_suggestion(db, suggestion_id)
    except SuggestionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/search")
@limiter.limit(EXPENSIVE_LIMIT)
def search(request: Request, body: SearchRequest, db: DbDep, _user: AdminUser):
    settings = get_settings()
    try:
        return search_jobs(
            db,
            query=body.query,
            api_key=settings.xai_api_key,
            model=settings.xai_model,
            base_url=settings.xai_base_url,
        )
    except FinderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
