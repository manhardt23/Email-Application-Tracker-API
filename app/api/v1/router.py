from fastapi import APIRouter

from app.api.v1 import applications, auth, emails, health, jobs, stats

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
