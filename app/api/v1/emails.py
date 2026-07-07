from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from starlette.requests import Request

from app.auth.dependencies import AdminUser, CurrentUser, get_db
from app.db.models import Email, EmailAnalysis
from app.db.repositories.analysis_repo import AnalysisRepository
from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository
from app.llm.base import EmailClassification
from app.middleware.rate_limit import EXPENSIVE_LIMIT, limiter

router = APIRouter()


DbDep = Annotated[Session, Depends(get_db)]
UNKNOWN_COMPANY = "Unknown Company"
UNKNOWN_POSITION = "Unknown Position"
DEFAULT_STAGE = "applied"


class EmailPromoteRequest(BaseModel):
    company_name: str | None = None
    position: str | None = None
    stage: str | None = None


def flatten_email(email: Email) -> dict:
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
        "application_id": a.application_id if a else None,
    }


@router.get("")
@limiter.limit(EXPENSIVE_LIMIT)
def list_emails(
    request: Request,
    db: DbDep,
    _user: AdminUser,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    total = db.query(Email).count()
    emails = (
        db.query(Email)
        .options(joinedload(Email.analysis))
        .order_by(Email.received_date.desc(), Email.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return {
        "items": [flatten_email(e) for e in emails],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/review")
@limiter.limit(EXPENSIVE_LIMIT)
def list_emails_for_review(
    request: Request,
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
    return [flatten_email(a.email) for a in analyses]


@router.post("/{email_id}/promote")
def promote_email_to_application(
    email_id: int,
    body: EmailPromoteRequest,
    db: DbDep,
    _user: AdminUser,
):
    email = (
        db.query(Email)
        .options(joinedload(Email.analysis))
        .filter(Email.id == email_id)
        .first()
    )
    if email is None:
        raise HTTPException(status_code=404, detail="Email not found")

    analysis = email.analysis

    company_name = (
        (body.company_name or "").strip()
        or ((analysis.detected_company if analysis else "") or "").strip()
        or UNKNOWN_COMPANY
    )
    position_name = (
        (body.position or "").strip()
        or ((analysis.detected_position if analysis else "") or "").strip()
        or UNKNOWN_POSITION
    )
    stage_value = (
        (body.stage or "").strip()
        or ((analysis.detected_stage if analysis else "") or "").strip()
        or DEFAULT_STAGE
    )

    company_repo = CompanyRepository(db)
    app_repo = ApplicationRepository(db)
    analysis_repo = AnalysisRepository(db)

    company = company_repo.find_or_create(company_name)
    existing = app_repo.find_by_company_and_position(company.id, position_name)
    created = existing is None
    application = existing or app_repo.find_or_create(company.id, position_name)

    if stage_value:
        application.stage = stage_value

    if analysis is None:
        classification = EmailClassification(
            is_application=True,
            company=company_name,
            position=position_name,
            stage=stage_value,
            confidence="low",
        )
        analysis = analysis_repo.create(
            email_id=email.id,
            classification=classification,
            model_used="manual_promotion",
            worker_run_id=None,
        )
    else:
        analysis.is_application = True
        if not analysis.detected_company:
            analysis.detected_company = company_name
        if not analysis.detected_position:
            analysis.detected_position = position_name
        if not analysis.detected_stage:
            analysis.detected_stage = stage_value

    analysis_repo.link_to_application(analysis, application.id)
    db.commit()
    db.refresh(application)

    return {
        "email_id": email.id,
        "application_id": application.id,
        "created": created,
        "company_name": company.name,
        "position": application.position,
        "stage": application.stage,
    }


@router.post("/{email_id}/dismiss")
def dismiss_email_from_review(email_id: int, db: DbDep, _user: AdminUser):
    """Clear an email's needs_review flag so it leaves the review queue."""
    email = (
        db.query(Email)
        .options(joinedload(Email.analysis))
        .filter(Email.id == email_id)
        .first()
    )
    if email is None:
        raise HTTPException(status_code=404, detail="Email not found")
    if email.analysis is None:
        raise HTTPException(status_code=404, detail="Email has no analysis to dismiss")
    email.analysis.needs_review = False
    db.commit()
    db.refresh(email)
    return flatten_email(email)
