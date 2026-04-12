from fastapi import APIRouter

from app.api.v1 import applications, emails, health, jobs

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
