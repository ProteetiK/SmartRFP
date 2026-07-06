"""
backend/security.py — API key authentication + role-based access + rate
limiting for production.

History note: this file (along with the root settings.py) existed on an
unmerged branch (origin/feature_likhitha) and never made it into `main`,
even though backend/main.py has always imported from it
(`from backend.security import limiter, require_api_key, require_role`).
That import was failing outright. This is a recovered + completed version:
the original only had `require_api_key` (a flat allow-list, no roles);
`require_role` is new, implementing the viewer/reviewer/admin hierarchy that
.env already documents in its API_KEYS comment but that was never actually
implemented anywhere.

Design:
  - Auth: a simple, real X-API-Key header check against settings.API_KEYS
    (a {key: role} mapping — see backend/config.py). Intentionally not
    OAuth/JWT — SmartRFP is a small internal tool, not a multi-tenant public
    API — but it is enforced server-side on every mutating/data route, fails
    closed, and is fully configurable via env.
  - Roles: viewer < reviewer < admin. A bare key with no ":role" suffix in
    API_KEYS defaults to "admin" so a pre-RBAC single-key setup keeps working
    unchanged.
  - Rate limiting: slowapi (a Flask-limiter-style wrapper for Starlette/
    FastAPI), keyed by API key when present, else by client IP. In-memory by
    default; point it at Redis via RATE_LIMIT_STORAGE_URI for multi-worker
    deployments.
"""
import logging

from fastapi import Header, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.config import settings

logger = logging.getLogger("smartrfp.security")

# viewer = read-only; reviewer = viewer + review/regenerate/audit;
# admin = reviewer + delete RFPs, write/sync the knowledge base.
_ROLE_RANK = {"viewer": 0, "reviewer": 1, "admin": 2}


def _rate_limit_key(request: Request) -> str:
    """Prefer the caller's API key as the rate-limit bucket (fairer than IP
    when several users share a NAT/VPN); fall back to remote address."""
    api_key = request.headers.get("x-api-key")
    return api_key or get_remote_address(request)


# Use Redis in multi-worker/production deployments so limits are shared
# across uvicorn workers and containers. Falls back to in-memory (per-process)
# storage for local dev — set RATE_LIMIT_STORAGE_URI=redis://redis:6379/0 in
# a real deployment.
limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    headers_enabled=True,  # adds X-RateLimit-* response headers
)


def require_api_key(x_api_key: str = Header(default=None, alias="X-API-Key")) -> str:
    """FastAPI dependency: enforce X-API-Key on protected (read) routes.

    Behavior:
      - If settings.REQUIRE_AUTH is False (local dev, ENVIRONMENT != production
        and REQUIRE_AUTH not explicitly set), auth is skipped entirely so
        local development isn't blocked.
      - If REQUIRE_AUTH is True, a missing/invalid key raises 401.
      - If REQUIRE_AUTH is True but no API_KEYS are configured, that's a
        misconfiguration — fail closed (503) rather than silently allowing
        every request through.
    """
    if not settings.REQUIRE_AUTH:
        return "auth-disabled"

    if not settings.API_KEYS:
        logger.error("REQUIRE_AUTH=true but no API_KEYS configured — refusing all requests.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server misconfiguration: authentication is required but no API keys are set.",
        )

    if not x_api_key or x_api_key not in settings.API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Send it in the 'X-API-Key' header.",
        )
    return x_api_key


def require_role(*allowed_roles: str):
    """FastAPI dependency FACTORY: enforce X-API-Key AND that its role meets
    (or exceeds) at least one of `allowed_roles` in the viewer < reviewer <
    admin hierarchy.

    Usage:
        @app.delete(...)
        def delete_rfp(..., _role: str = Depends(require_role("admin"))): ...

        @app.put(...)
        def review(..., _role: str = Depends(require_role("reviewer", "admin"))): ...

    When settings.REQUIRE_AUTH is False, this behaves like require_api_key
    and skips the role check entirely (local dev default).
    """
    min_rank = min(_ROLE_RANK.get(r, 99) for r in allowed_roles) if allowed_roles else 0

    def _dependency(x_api_key: str = Header(default=None, alias="X-API-Key")) -> str:
        if not settings.REQUIRE_AUTH:
            return "auth-disabled"

        if not settings.API_KEYS:
            logger.error("REQUIRE_AUTH=true but no API_KEYS configured — refusing all requests.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server misconfiguration: authentication is required but no API keys are set.",
            )

        if not x_api_key or x_api_key not in settings.API_KEYS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid API key. Send it in the 'X-API-Key' header.",
            )

        role = settings.API_KEYS[x_api_key]
        rank = _ROLE_RANK.get(role, -1)
        if rank < min_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(f"API key role '{role}' is not permitted here; "
                        f"requires one of {sorted(allowed_roles)}."),
            )
        return role

    return _dependency