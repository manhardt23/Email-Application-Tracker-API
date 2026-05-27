from fastapi import APIRouter

from app.api.v1 import applications, auth, dashboard, emails, health, jobs

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
