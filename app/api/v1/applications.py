from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser, get_db
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
def list_applications(db: DbDep, _user: AdminUser, stage: str | None = None):
    repo = ApplicationRepository(db)
    results = repo.get_by_stage(stage) if stage else repo.get_all()
    if not results:
        detail = f"No applications found with stage '{stage}'" if stage else "No applications found"
        raise HTTPException(status_code=404, detail=detail)
    return results


@router.get("/{application_id}")
def get_application(application_id: int, db: DbDep, _user: AdminUser):
    result = ApplicationRepository(db).get_by_id(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Application not found")
    return result


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
