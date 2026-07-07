import traceback
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth.dependencies import AdminUser, get_db
from app.db.models import WorkerRun
from app.db.repositories.worker_run_repo import WorkerRunRepository
from app.middleware.rate_limit import EXPENSIVE_LIMIT, limiter
from app.services.worker_runtime import set_max_emails_override

router = APIRouter()


DbDep = Annotated[Session, Depends(get_db)]


def _serialize_run(run: WorkerRun) -> dict:
    return {
        "job_id": str(run.id),
        "status": run.status,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "emails_fetched": run.emails_fetched,
        "emails_saved": run.emails_saved,
        "applications_found": run.applications_found,
        "error_message": run.error_message,
    }


class WorkerEmailLimitUpdate(BaseModel):
    max_emails_per_run: int = Field(..., ge=1, le=1000)


class BackfillRequest(BaseModel):
    from_date: datetime
    to_date: datetime | None = None
    max_emails: int | None = Field(default=None, ge=1, le=1000)


def _run_worker(
    run_id: int,
    backfill_from: datetime | None = None,
    backfill_to: datetime | None = None,
    backfill_max_emails: int | None = None,
) -> None:
    from app.worker import run  # deferred to avoid circular imports
    try:
        run(
            worker_run_id=run_id,
            backfill_from=backfill_from,
            backfill_to=backfill_to,
            backfill_max_emails=backfill_max_emails,
        )
    except Exception as e:
        # worker.py already calls repo.fail() internally; just log here.
        print(f"Job {run_id} failed: {e}")
        traceback.print_exc()


@router.post("/email-check", status_code=202)
@limiter.limit(EXPENSIVE_LIMIT)
def trigger_email_check(
    request: Request,
    background_tasks: BackgroundTasks,
    db: DbDep,
    _user: AdminUser,
):
    repo = WorkerRunRepository(db)
    run = repo.try_create_queued_run()
    if run is None:
        raise HTTPException(status_code=409, detail="An email check is already running")
    db.commit()
    db.refresh(run)
    run_id = run.id
    background_tasks.add_task(_run_worker, run_id)
    return {"job_id": str(run_id), "status": "queued"}


@router.post("/email-backfill", status_code=202)
@limiter.limit(EXPENSIVE_LIMIT)
def trigger_email_backfill(
    request: Request,
    body: BackfillRequest,
    background_tasks: BackgroundTasks,
    db: DbDep,
    _user: AdminUser,
):
    from_date = body.from_date if body.from_date.tzinfo else body.from_date.replace(tzinfo=UTC)
    to_date = body.to_date or datetime.now(UTC)
    to_date = to_date if to_date.tzinfo else to_date.replace(tzinfo=UTC)
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be before or equal to to_date")

    repo = WorkerRunRepository(db)
    run = repo.try_create_queued_run()
    if run is None:
        raise HTTPException(status_code=409, detail="An email check is already running")
    db.commit()
    db.refresh(run)
    run_id = run.id
    background_tasks.add_task(
        _run_worker,
        run_id,
        from_date,
        to_date,
        body.max_emails,
    )
    return {"job_id": str(run_id), "status": "queued"}


@router.post("/email-limit")
def set_worker_email_limit(body: WorkerEmailLimitUpdate, _user: AdminUser):
    override = set_max_emails_override(body.max_emails_per_run)
    return {"max_emails_per_run": override, "source": "in_memory_override"}


@router.get("")
def list_jobs(db: DbDep, _user: AdminUser, limit: int = Query(20, ge=1, le=100)):
    """Recent worker runs, newest first — powers the Jobs & workers history table."""
    runs = WorkerRunRepository(db).get_recent(limit)
    return [_serialize_run(r) for r in runs]


@router.get("/{job_id}")
def get_job_status(job_id: str, db: DbDep, _user: AdminUser):
    try:
        run_id = int(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")
    run = WorkerRunRepository(db).get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_run(run)
