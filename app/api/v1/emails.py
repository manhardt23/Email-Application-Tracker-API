from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.database import SessionLocal
from app.db.models import Email, EmailAnalysis
from app.db.repositories.email_repo import EmailRepository
from app.db.repositories.analysis_repo import AnalysisRepository

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


def _flatten(email: Email) -> dict:
    a: EmailAnalysis | None = email.analysis
    return {
        "id": email.id,
        "message_id": email.message_id,
        "uid": email.uid,
        "sender": email.sender,
        "subject": email.subject,
        "received_date": email.received_date,
        "created_at": email.created_at,
        "is_application": a.is_application if a else None,
        "detected_company": a.detected_company if a else None,
        "detected_position": a.detected_position if a else None,
        "detected_stage": a.detected_stage if a else None,
        "confidence": a.confidence if a else None,
        "needs_review": a.needs_review if a else None,
    }


@router.get("")
def list_emails(db: DbDep):
    emails = (
        db.query(Email)
        .options(joinedload(Email.analysis))
        .order_by(Email.received_date.desc())
        .all()
    )
    if not emails:
        raise HTTPException(status_code=404, detail="No emails found")
    return [_flatten(e) for e in emails]


@router.get("/review")
def list_emails_for_review(db: DbDep):
    analyses = (
        db.query(EmailAnalysis)
        .filter(EmailAnalysis.needs_review == True)  # noqa: E712
        .options(joinedload(EmailAnalysis.email))
        .all()
    )
    if not analyses:
        raise HTTPException(status_code=404, detail="No emails needing review")
    return [_flatten(a.email) for a in analyses]
