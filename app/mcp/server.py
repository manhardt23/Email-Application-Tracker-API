"""Streamable HTTP MCP server. Auth is a long-lived bearer, not a user login."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.mcp import tools as tool_impls
from app.mcp.auth import credential_is_valid
from app.middleware.rate_limit import limiter

_INSTRUCTIONS = (
    "Read applications and manage job suggestions plus the job-finder profile. "
    "Job-site logins are not available. "
    "This server cannot send or check email, run a backfill, manage users, "
    "delete records, or change secrets."
)


class McpBearerMiddleware:
    """Reject the request unless Authorization is the configured MCP bearer."""

    def __init__(self, app: ASGIApp):
        self.app = app
        # slowapi names the matched endpoint as module.__name__. An ASGI instance
        # has no __name__, so a /mcp call raised AttributeError and returned 500
        # before this bearer check could answer 401.
        self.__name__ = "mcp_endpoint"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if not credential_is_valid(Headers(scope=scope).get("authorization")):
            response = JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing MCP credential"},
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def build_mcp() -> FastMCP:
    mcp = FastMCP(
        "Email Application Tracker",
        instructions=_INSTRUCTIONS,
        host="0.0.0.0",
        stateless_http=True,
        json_response=True,
        streamable_http_path="/",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @mcp.tool()
    def list_applications(
        limit: Annotated[
            int, Field(ge=1, le=1000, description="Maximum rows, from 1 to 1000.")
        ] = 1000,
        offset: Annotated[int, Field(ge=0, description="Rows to skip.")] = 0,
    ) -> dict:
        """List tracked applications as company, title, and stage.

        Each item also has id. Use the list to skip roles that are already
        applications. Does not return email content.
        """
        return tool_impls.list_applications(limit=limit, offset=offset)

    @mcp.tool()
    def get_application(
        application_id: Annotated[int, Field(ge=1, description="Application id.")],
    ) -> dict:
        """Get one application: company, title, stage, notes, and dates. No emails."""
        return tool_impls.get_application(application_id)

    @mcp.tool()
    def list_job_suggestions() -> dict:
        """List stored job suggestions, hiding roles that match an application."""
        return tool_impls.list_job_suggestions()

    @mcp.tool()
    def create_job_suggestion(
        title: Annotated[str, Field(description="Job title.")],
        company: Annotated[str, Field(description="Company name.")],
        apply_url: Annotated[str, Field(description="http or https application link.")],
        pay: Annotated[str | None, Field(description="Pay text, or omit when unknown.")] = None,
        requirements_summary: Annotated[str, Field(description="Short requirements text.")] = "",
    ) -> dict:
        """Create one job suggestion. Does not search the web and stores no site login."""
        return tool_impls.create_job_suggestion(
            title=title,
            company=company,
            apply_url=apply_url,
            pay=pay,
            requirements_summary=requirements_summary,
        )

    @mcp.tool()
    def update_job_suggestion(
        suggestion_id: Annotated[int, Field(ge=1, description="Suggestion id.")],
        title: Annotated[str | None, Field(description="New title. Omit to leave it.")] = None,
        company: Annotated[str | None, Field(description="New company. Omit to leave it.")] = None,
        pay: Annotated[
            str | None,
            Field(description="New pay text. Pass an empty string to clear it. Omit to leave it."),
        ] = None,
        requirements_summary: Annotated[
            str | None, Field(description="New requirements text. Omit to leave it.")
        ] = None,
        apply_url: Annotated[
            str | None, Field(description="New http or https link. Omit to leave it.")
        ] = None,
    ) -> dict:
        """Update one job suggestion. Does not delete it."""
        return tool_impls.update_job_suggestion(
            suggestion_id,
            title=title,
            company=company,
            pay=pay,
            requirements_summary=requirements_summary,
            apply_url=apply_url,
        )

    @mcp.tool()
    def get_job_finder_profile() -> dict:
        """Read the job-finder profile: target titles and skills."""
        return tool_impls.get_job_finder_profile()

    @mcp.tool()
    def update_job_finder_profile(
        target_titles: Annotated[str, Field(description="Target job titles.")] = "",
        skills: Annotated[str, Field(description="Skills to compare postings against.")] = "",
    ) -> dict:
        """Replace the job-finder profile. Both fields are saved as given."""
        return tool_impls.update_job_finder_profile(target_titles=target_titles, skills=skills)

    return mcp


def protected_mcp_app(mcp: FastMCP) -> ASGIApp:
    """ASGI app for streamable HTTP, wrapped with the bearer check.

    Call this before the process starts serving so the session manager exists.
    The caller runs ``mcp.session_manager.run()`` in the FastAPI lifespan.
    """
    mcp.streamable_http_app()
    endpoint = McpBearerMiddleware(StreamableHTTPASGIApp(mcp.session_manager))
    # Register the name only. exempt() also returns a sync wrapper, which
    # Starlette would treat as a request function instead of this ASGI app.
    limiter.exempt(endpoint)
    return endpoint
