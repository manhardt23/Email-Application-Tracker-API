"""Unit tests for rate-limit key extraction and 429 behavior."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request

from app.middleware.rate_limit import (
    build_limiter,
    configure_rate_limiting,
    get_client_ip,
    get_rate_limit_key,
)


def _make_request(
    *,
    forwarded_for: str | None = None,
    real_ip: str | None = None,
    authorization: str | None = None,
    client_host: str = "127.0.0.1",
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    if real_ip is not None:
        headers.append((b"x-real-ip", real_ip.encode()))
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "client": (client_host, 0),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
    }
    return Request(scope)


def test_get_client_ip_prefers_x_forwarded_for():
    request = _make_request(forwarded_for="203.0.113.1, 10.0.0.1")
    assert get_client_ip(request) == "203.0.113.1"


def test_get_client_ip_falls_back_to_x_real_ip():
    request = _make_request(real_ip="198.51.100.2")
    assert get_client_ip(request) == "198.51.100.2"


def test_get_client_ip_falls_back_to_direct_client():
    request = _make_request(client_host="10.1.2.3")
    assert get_client_ip(request) == "10.1.2.3"


def test_get_rate_limit_key_uses_ip_when_unauthenticated():
    request = _make_request(forwarded_for="203.0.113.9")
    assert get_rate_limit_key(request) == "ip:203.0.113.9"


def test_get_rate_limit_key_uses_username_from_valid_jwt(monkeypatch):
    from app.config import Settings

    settings = Settings(
        email_user="u",
        email_pass="p",
        database_url="sqlite://",
        jwt_secret="test-secret",
    )

    def _fake_settings():
        return settings

    monkeypatch.setattr("app.middleware.rate_limit.get_settings", _fake_settings)
    monkeypatch.setattr("app.auth.jwt_handler.get_settings", _fake_settings)

    from app.auth.jwt_handler import create_access_token

    token = create_access_token("alice", "admin")
    request = _make_request(authorization=f"Bearer {token}")
    assert get_rate_limit_key(request) == "user:alice"


def test_get_rate_limit_key_falls_back_to_ip_for_invalid_jwt():
    request = _make_request(authorization="Bearer not-a-jwt", client_host="10.9.8.7")
    assert get_rate_limit_key(request) == "ip:10.9.8.7"


def test_build_limiter_disabled_has_no_default_limits():
    from app.config import Settings

    settings = Settings(
        email_user="u",
        email_pass="p",
        database_url="sqlite://",
        rate_limit_enabled=False,
    )
    test_limiter = build_limiter(settings)
    assert test_limiter.enabled is False
    assert test_limiter._default_limits == []


def test_rate_limit_returns_429_when_exceeded():
    test_limiter = Limiter(key_func=lambda request: "test-key", default_limits=["2/minute"])
    app = FastAPI()
    app.state.limiter = test_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/ping")
    @test_limiter.limit("2/minute")
    def ping(request: Request):
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 429


def test_configure_rate_limiting_skips_middleware_when_disabled(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()

    from app.config import Settings

    settings = Settings(
        email_user="u",
        email_pass="p",
        database_url="sqlite://",
        rate_limit_enabled=False,
    )
    disabled_limiter = build_limiter(settings)
    monkeypatch.setattr("app.middleware.rate_limit.limiter", disabled_limiter)

    app = FastAPI()
    configure_rate_limiting(app)

    assert app.state.limiter.enabled is False
    assert not any(m.cls is SlowAPIMiddleware for m in app.user_middleware)

    get_settings.cache_clear()
