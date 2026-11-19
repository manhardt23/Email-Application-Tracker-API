import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Route
from starlette.staticfiles import StaticFiles

from app.api.v1.stats import router as stats_router
from app.db import models
from app.db.database import engine
from app.mcp.auth import mcp_credential_configured
from app.mcp.server import build_mcp, protected_mcp_app
from app.middleware.rate_limit import configure_rate_limiting

logger = logging.getLogger(__name__)


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            if path.startswith(("api/", "docs", "openapi.json", "redoc", "stats", "mcp")):
                raise
            return await super().get_response("index.html", scope)


def create_app() -> FastAPI:
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    mcp = build_mcp()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Ensure tables exist on startup.
        # Phase 2 will replace this with `alembic upgrade head`.
        models.Base.metadata.create_all(bind=engine)
        if not mcp_credential_configured():
            logger.warning(
                "MCP_BEARER_TOKEN is not set. MCP requests are rejected until it is configured."
            )
        async with mcp.session_manager.run():
            yield

    app = FastAPI(
        title="Email Application Tracker",
        version="0.1.0",
        lifespan=lifespan,
    )
    from app.api.v1.router import api_router

    configure_rate_limiting(app)

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(stats_router, prefix="/stats", tags=["stats"])
    # A route, not a mount: Starlette mounts only match /mcp/..., and the SPA
    # mount would otherwise catch a client calling /mcp.
    mcp_asgi = protected_mcp_app(mcp)
    app.router.routes.append(
        Route(
            "/mcp",
            endpoint=mcp_asgi,
            methods=["GET", "POST", "DELETE"],
            include_in_schema=False,
            name="mcp",
        )
    )
    app.router.routes.append(
        Route(
            "/mcp/",
            endpoint=mcp_asgi,
            methods=["GET", "POST", "DELETE"],
            include_in_schema=False,
            name="mcp-slash",
        )
    )
    app.mount(
        "/",
        SPAStaticFiles(directory=str(frontend_dist), check_dir=False, html=True),
        name="frontend",
    )
    return app


app = create_app()
