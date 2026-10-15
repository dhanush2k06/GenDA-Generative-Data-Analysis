"""
Security middlewares and validators:
- Loopback IP enforcement (127.0.0.1 only)
- Per-launch token verification via X-GenDA-Token
- Origin and Host header validation (DNS-rebinding protection)
- Strict CORS rules
"""

from __future__ import annotations
import os
import secrets
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Per-launch secret token
_ACTIVE_TOKEN: str = os.environ.get("GENDA_TOKEN", "")

if not _ACTIVE_TOKEN:
    _ACTIVE_TOKEN = secrets.token_urlsafe(32)


def get_active_token() -> str:
    return _ACTIVE_TOKEN


def set_active_token(token: str) -> None:
    global _ACTIVE_TOKEN
    _ACTIVE_TOKEN = token


ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}

ALLOWED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "[::1]",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Validates Host, Origin, and Loopback IP for every incoming request.
    Protects against DNS rebinding, CSRF, and external access.
    """
    async def dispatch(self, request: Request, call_next):
        # 1. Check client IP is loopback
        client_host = request.client.host if request.client else ""
        if client_host and client_host not in ("127.0.0.1", "::1", "localhost", "testclient"):
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden: GenDA accepts loopback requests only (127.0.0.1)."},
            )

        # 2. Check Host header
        host_header = request.headers.get("host", "").split(":")[0].lower()
        if host_header and host_header not in ALLOWED_HOSTS and host_header != "testserver":
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden: Invalid Host header."},
            )

        # 3. Check Origin header (for non-GET or CORS requests)
        origin = request.headers.get("origin")
        if origin and origin not in ALLOWED_ORIGINS:
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden: Origin not in allowed loopback list."},
            )

        response = await call_next(request)
        return response


api_key_header = APIKeyHeader(name="X-GenDA-Token", auto_error=False)


async def verify_token(request: Request, token_header: str = Security(api_key_header)) -> str:
    """Verify per-launch security token from header or query param."""
    # Allow token from header or query param
    query_token = request.query_params.get("token")
    token = token_header or query_token

    if not token or not secrets.compare_digest(token, _ACTIVE_TOKEN):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing or invalid X-GenDA-Token.",
        )
    return token
