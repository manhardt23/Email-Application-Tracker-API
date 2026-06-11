from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.api.v1.emails import flatten_email
from app.auth.dependencies import AdminUser, get_db
from app.db.models import EmailAnalysis
from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository

router = APIRouter()


DbDep = Annotated[Session, Depends(get_db)]


class StageEnum(StrEnum):
    applied = "applied"
    rejected = "rejected"
    interview = "interview"
    offer = "offer"
    assessment = "assessment"
    other = "other"


class ApplicationUpdate(BaseModel):
    stage: StageEnum | None = None
    notes: str | None = None
    company_name: str | None = None
    position: str | None = None


@router.get("")
def list_applications(
    db: DbDep,
    _user: AdminUser,
    stage: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items, total = ApplicationRepository(db).search(
        stage=stage, q=q, limit=limit, offset=offset
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{application_id}")
def get_application(application_id: int, db: DbDep, _user: AdminUser):
    result = ApplicationRepository(db).get_by_id(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Application not found")
    return result


@router.get("/{application_id}/emails")
def list_application_emails(application_id: int, db: DbDep, _user: AdminUser):
    """Emails linked to this application, newest first — powers the detail timeline."""
    application = ApplicationRepository(db).get_by_id(application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    analyses = (
        db.query(EmailAnalysis)
        .options(joinedload(EmailAnalysis.email))
        .filter(EmailAnalysis.application_id == application_id)
        .all()
    )
    emails = [a.email for a in analyses if a.email is not None]
    emails.sort(key=lambda e: e.received_date, reverse=True)
    return [flatten_email(e) for e in emails]


@router.put("/{application_id}")
def update_application(application_id: int, body: ApplicationUpdate, db: DbDep, _user: AdminUser):
    repo = ApplicationRepository(db)
    company_repo = CompanyRepository(db)
    application = repo.get_by_id(application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if "stage" in body.model_fields_set:
        if body.stage is None:
            raise HTTPException(status_code=422, detail="stage cannot be null")
        application.stage = body.stage.value
    if "notes" in body.model_fields_set:
        application.notes = body.notes
    target_company_id = application.company_id
    target_position = application.position

    if "company_name" in body.model_fields_set:
        if body.company_name is None or not body.company_name.strip():
            raise HTTPException(status_code=422, detail="company_name cannot be null or empty")
        company = company_repo.find_or_create(body.company_name.strip())
        target_company_id = company.id
        application.company_id = company.id

    if "position" in body.model_fields_set:
        if body.position is None or not body.position.strip():
            raise HTTPException(status_code=422, detail="position cannot be null or empty")
        target_position = body.position.strip()
        application.position = target_position

    if target_position is not None:
        existing = repo.find_by_company_and_position(target_company_id, target_position)
        if existing and existing.id != application.id:
            raise HTTPException(
                status_code=409,
                detail="An application already exists for that company and position",
            )
    db.commit()
    db.refresh(application)
    return application
