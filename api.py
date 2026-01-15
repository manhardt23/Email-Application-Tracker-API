from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from email_tracker.DB import models
from sqlalchemy.orm import Session
from typing import Annotated
from pydantic import BaseModel
from email_tracker.DB.database import SessionLocal, engine
import tracker
import uuid
from config import get_email_limit



app = FastAPI()
models.Base.metadata.create_all(bind=engine)

class JobStatus:
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

jobs = {}

class Applications(BaseModel):
    position: str
    stage: str

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]

@app.get("/applications/{application_id}")
async def read_application(application_id: int, db: db_dependency):
    result = db.query(models.Application).filter(models.Application.id == application_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="application not found")
    return result

@app.get("/applications")
async def read_application(db: db_dependency):
    result = db.query(models.Application).all()
    if not result:
        raise HTTPException(status_code=404, detail="applications not found")
    return result

def has_active_job():
    return any(
        status in ("pending", "running")
        for status in jobs.values()
    )

@app.post("/run-email-check", status_code=202)
def run_email_checker(background_tasks: BackgroundTasks):
    if has_active_job():
        raise HTTPException(status_code=409, detail="Already running please wait")
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobStatus.pending

    background_tasks.add_task(run_tracker_job, job_id)

    return {
        "job_id": job_id,
        "status": "pending"
    }


def run_tracker_job(job_id: str):
    try:
        jobs[job_id] = JobStatus.running
        tracker.main(get_email_limit())
        jobs[job_id] = JobStatus.completed
    except Exception:
        jobs[job_id] = JobStatus.failed
        raise


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job_id,
        "status": jobs[job_id]
    }

