from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import engine
from app.db import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist on startup.
    # Phase 2 will replace this with `alembic upgrade head`.
    models.Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Email Application Tracker",
        version="0.1.0",
        lifespan=lifespan,
    )
    from app.api.v1.router import api_router
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
