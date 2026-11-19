"""Bearer check for the MCP endpoint.

The credential is MCP_BEARER_TOKEN from the environment (or a secrets manager
that injects that variable). It is not a user JWT and it does not expire when
a login session ends. There is no second user store.
"""

from __future__ import annotations

import hmac

from app.config import get_settings

_MAX_PRESENTED_TOKEN = 4096


def mcp_credential_configured() -> bool:
    return bool(get_settings().mcp_bearer_token)


def presented_bearer(authorization: str | None) -> str | None:
    """Return the bearer value, or None when the header is missing or not Bearer."""
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = value.strip()
    if not token or len(token) > _MAX_PRESENTED_TOKEN:
        return None
    return token


def credential_is_valid(authorization: str | None) -> bool:
    """True only when a configured secret matches the Authorization bearer."""
    expected = get_settings().mcp_bearer_token
    presented = presented_bearer(authorization)
    if not expected or presented is None:
        return False
    try:
        return hmac.compare_digest(presented, expected)
    except (TypeError, ValueError):
        return False
