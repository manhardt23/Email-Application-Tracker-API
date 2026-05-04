from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import CurrentUser, get_db
from app.db.models import Email, EmailAnalysis

router = APIRouter()


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
def list_emails(
    db: DbDep,
    _user: CurrentUser,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    emails = (
        db.query(Email)
        .options(joinedload(Email.analysis))
        .order_by(Email.received_date.desc(), Email.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [_flatten(e) for e in emails]


@router.get("/review")
def list_emails_for_review(
    db: DbDep,
    _user: CurrentUser,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    analyses = (
        db.query(EmailAnalysis)
        .filter(EmailAnalysis.needs_review == True)  # noqa: E712
        .options(joinedload(EmailAnalysis.email))
        .order_by(EmailAnalysis.id.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [_flatten(a.email) for a in analyses]
