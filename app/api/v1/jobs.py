import traceback
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.repositories.worker_run_repo import WorkerRunRepository

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


def _run_worker(run_id: int) -> None:
    from app.worker import run  # deferred to avoid circular imports
    try:
        run(worker_run_id=run_id)
    except Exception as e:
        # worker.py already calls repo.fail() internally; just log here.
        print(f"Job {run_id} failed: {e}")
        traceback.print_exc()


@router.post("/email-check", status_code=202)
def trigger_email_check(background_tasks: BackgroundTasks, db: DbDep):
    repo = WorkerRunRepository(db)
    run = repo.try_create_running_run()
    if run is None:
        raise HTTPException(status_code=409, detail="An email check is already running")
    db.commit()
    db.refresh(run)
    run_id = run.id
    background_tasks.add_task(_run_worker, run_id)
    return {"job_id": str(run_id), "status": "running"}


@router.get("/{job_id}")
def get_job_status(job_id: str, db: DbDep):
    try:
        run_id = int(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")
    run = WorkerRunRepository(db).get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Job not found")
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
