from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
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
