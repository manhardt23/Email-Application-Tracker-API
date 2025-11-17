from fastapi import FastAPI, HTTPException, Depends, Query, Body
from email_tracker.DB import models
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from pydantic import BaseModel
import tracker
import config

app = FastAPI()


def get_db():
    """Dependency to get database session"""
    db = next(models.get_db())
    try:
        yield db
    finally:
        db.close()


@app.get("/api/v1/")
async def root():
    return {"message": "Hello World"}


@app.get("/api/v1/emails")
def get_all_emails(db: Session = Depends(get_db)):
    emails = db.query(models.ApplicationEmail).all()
    if not emails:
        return {"message": "No emails found"}
    return emails


@app.post("/api/v1/run")
def run_tracker(limit: Optional[int] = Query(None, description="Number of emails to process")):
    """
    Run the email tracker pipeline.
    If limit is not provided, uses the default limit from config.
    """
    try:
        # Use provided limit or default from config
        if limit is None:
            limit = config.get_email_limit()
        
        if limit < 1:
            raise HTTPException(status_code=400, detail="Limit must be a positive integer")
        
        # Run the tracker pipeline
        tracker.main(limit)
        
        # Get summary statistics
        db = next(models.get_db())
        try:
            total_emails = db.query(func.count(models.ApplicationEmail.id)).scalar() or 0
            total_applications = db.query(func.count(models.Application.id)).scalar() or 0
            total_companies = db.query(func.count(models.Company.id)).scalar() or 0
            
            return {
                "status": "success",
                "message": f"Processed {limit} emails",
                "statistics": {
                    "total_emails_in_db": total_emails,
                    "total_applications": total_applications,
                    "total_companies": total_companies
                }
            }
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running tracker: {str(e)}")


class LimitUpdate(BaseModel):
    limit: int


@app.get("/api/v1/config/limit")
def get_limit():
    """Get the current default email limit"""
    try:
        limit = config.get_email_limit()
        return {"limit": limit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting limit: {str(e)}")


@app.put("/api/v1/config/limit")
def update_limit(limit_data: LimitUpdate = Body(...)):
    """Update the default email limit"""
    try:
        new_limit = config.set_email_limit(limit_data.limit)
        return {
            "status": "success",
            "message": f"Limit updated to {new_limit}",
            "limit": new_limit
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating limit: {str(e)}")


@app.get("/api/v1/status")
def get_status(db: Session = Depends(get_db)):
    """Get API health status and pipeline statistics"""
    try:
        # Get statistics from database
        total_emails = db.query(func.count(models.ApplicationEmail.id)).scalar() or 0
        total_applications = db.query(func.count(models.Application.id)).scalar() or 0
        total_companies = db.query(func.count(models.Company.id)).scalar() or 0
        emails_needing_review = db.query(func.count(models.ApplicationEmail.id)).filter(
            models.ApplicationEmail.needs_review == True
        ).scalar() or 0
        
        # Get stage distribution
        stage_counts = db.query(
            models.Application.stage,
            func.count(models.Application.id)
        ).group_by(models.Application.stage).all()
        
        stages = {stage: count for stage, count in stage_counts}
        
        # Get confidence distribution
        confidence_counts = db.query(
            models.ApplicationEmail.confidence,
            func.count(models.ApplicationEmail.id)
        ).filter(
            models.ApplicationEmail.confidence.isnot(None)
        ).group_by(models.ApplicationEmail.confidence).all()
        
        confidence = {conf: count for conf, count in confidence_counts}
        
        return {
            "status": "healthy",
            "api": {
                "version": "v1",
                "status": "operational"
            },
            "statistics": {
                "total_emails": total_emails,
                "total_applications": total_applications,
                "total_companies": total_companies,
                "emails_needing_review": emails_needing_review,
                "applications_by_stage": stages,
                "emails_by_confidence": confidence
            },
            "config": {
                "default_email_limit": config.get_email_limit()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")