from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth.dependencies import get_db
from app.db.models import Email, EmailAnalysis, WorkerRun
from app.middleware.rate_limit import PUBLIC_LIMIT, get_client_ip, limiter

router = APIRouter()

DbDep = Annotated[Session, Depends(get_db)]


@router.get("")
@limiter.limit(PUBLIC_LIMIT, key_func=get_client_ip, override_defaults=True)
def get_stats(request: Request, db: DbDep):
    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)

    total_emails_processed = db.query(func.count(Email.id)).scalar() or 0
    job_related_emails = (
        db.query(func.count(EmailAnalysis.id))
        .filter(EmailAnalysis.is_application.is_(True))
        .scalar()
        or 0
    )
    worker_last_ran_at = (
        db.query(func.max(WorkerRun.finished_at))
        .filter(WorkerRun.status == "completed")
        .scalar()
    )
    worker_run_count_7d = (
        db.query(func.count(WorkerRun.id))
        .filter(WorkerRun.status == "completed")
        .filter(WorkerRun.finished_at.is_not(None))
        .filter(WorkerRun.finished_at >= seven_days_ago)
        .scalar()
        or 0
    )

    return {
        "total_emails_processed": total_emails_processed,
        "job_related_emails": job_related_emails,
        "worker_last_ran_at": worker_last_ran_at,
        "worker_run_count_7d": worker_run_count_7d,
    }
