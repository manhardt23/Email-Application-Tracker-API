from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles

from app.api.v1.stats import router as stats_router
from app.db import models
from app.db.database import engine


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            if path.startswith(("api/", "docs", "openapi.json", "redoc", "stats")):
                raise
            return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist on startup.
    # Phase 2 will replace this with `alembic upgrade head`.
    models.Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    app = FastAPI(
        title="Email Application Tracker",
        version="0.1.0",
        lifespan=lifespan,
    )
    from app.api.v1.router import api_router

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(stats_router, prefix="/stats", tags=["stats"])
    app.mount(
        "/",
        SPAStaticFiles(directory=str(frontend_dist), check_dir=False, html=True),
        name="frontend",
    )
    return app


app = create_app()
