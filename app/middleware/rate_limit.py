"""Rate limiting via slowapi — per-IP for public routes, per-user when authenticated."""

from __future__ import annotations

from jose import JWTError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.auth.jwt_handler import decode_access_token
from app.config import Settings, get_settings


def get_client_ip(request: Request) -> str:
    """Resolve client IP behind Nginx (X-Forwarded-For / X-Real-IP) or direct."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return get_remote_address(request)


def get_rate_limit_key(request: Request) -> str:
    """Prefer authenticated username; fall back to client IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            payload = decode_access_token(token)
            username = payload.get("sub")
            if username:
                return f"user:{username}"
        except JWTError:
            pass
    return f"ip:{get_client_ip(request)}"


def build_limiter(settings: Settings) -> Limiter:
    return Limiter(
        key_func=get_rate_limit_key,
        default_limits=[settings.rate_limit_global] if settings.rate_limit_enabled else [],
        enabled=settings.rate_limit_enabled,
    )


_settings = get_settings()
limiter = build_limiter(_settings)

LOGIN_LIMIT = _settings.rate_limit_login
PUBLIC_LIMIT = _settings.rate_limit_public
EXPENSIVE_LIMIT = _settings.rate_limit_expensive


def configure_rate_limiting(app) -> None:
    """Attach limiter state, 429 handler, and middleware to the FastAPI app."""
    app.state.limiter = limiter
    if not limiter.enabled:
        return
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
