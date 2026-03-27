import traceback
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

router = APIRouter()

# NOTE: In-memory job store — Phase 5 replaces this with DB-backed worker_runs table.
_jobs: dict[str, str] = {}


class _Status:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def _has_active_job() -> bool:
    return any(s in (_Status.PENDING, _Status.RUNNING) for s in _jobs.values())


def _run_worker(job_id: str) -> None:
    try:
        _jobs[job_id] = _Status.RUNNING
        print(f"Job {job_id} started")
        from app.worker import run  # deferred to avoid circular imports
        run()
        _jobs[job_id] = _Status.COMPLETED
        print(f"Job {job_id} completed")
    except Exception as e:
        _jobs[job_id] = _Status.FAILED
        print(f"Job {job_id} failed: {e}")
        traceback.print_exc()


@router.post("/email-check", status_code=202)
def trigger_email_check(background_tasks: BackgroundTasks):
    if _has_active_job():
        raise HTTPException(status_code=409, detail="An email check is already running")
    job_id = str(uuid.uuid4())
    _jobs[job_id] = _Status.PENDING
    background_tasks.add_task(_run_worker, job_id)
    return {"job_id": job_id, "status": "pending"}


@router.get("/{job_id}")
def get_job_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": _jobs[job_id]}
