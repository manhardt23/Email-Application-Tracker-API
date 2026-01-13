from fastapi import FastAPI, HTTPException, Depends
from email_tracker.DB import models
from sqlalchemy.orm import Session
from typing import Annotated
from pydantic import BaseModel
from email_tracker.DB.database import SessionLocal, engine


app = FastAPI()
models.Base.metadata.create_all(bind=engine)

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