import logging

from fastapi import Header, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.config import settings

logger = logging.getLogger("smartrfp.security")

_ROLE_RANK = {"viewer": 0, "reviewer": 1, "admin": 2}


def _rate_limit_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    return api_key or get_remote_address(request)

limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    headers_enabled=True,  # adds X-RateLimit-* response headers
)


def require_api_key(x_api_key: str = Header(default=None, alias="X-API-Key")) -> str:
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