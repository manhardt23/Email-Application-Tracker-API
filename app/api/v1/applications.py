from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.repositories.application_repo import ApplicationRepository

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


class StageEnum(str, Enum):
    applied = "applied"
    rejected = "rejected"
    interview = "interview"
    offer = "offer"
    assessment = "assessment"
    other = "other"


class ApplicationUpdate(BaseModel):
    stage: StageEnum | None = None
    notes: str | None = None


@router.get("")
def list_applications(db: DbDep, stage: str | None = None):
    repo = ApplicationRepository(db)
    results = repo.get_by_stage(stage) if stage else repo.get_all()
    if not results:
        detail = f"No applications found with stage '{stage}'" if stage else "No applications found"
        raise HTTPException(status_code=404, detail=detail)
    return results


@router.get("/{application_id}")
def get_application(application_id: int, db: DbDep):
    result = ApplicationRepository(db).get_by_id(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Application not found")
    return result


@router.put("/{application_id}")
def update_application(application_id: int, body: ApplicationUpdate, db: DbDep):
    repo = ApplicationRepository(db)
    application = repo.get_by_id(application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if "stage" in body.model_fields_set:
        if body.stage is None:
            raise HTTPException(status_code=422, detail="stage cannot be null")
        application.stage = body.stage.value
    if "notes" in body.model_fields_set:
        application.notes = body.notes
    db.commit()
    db.refresh(application)
    return application
