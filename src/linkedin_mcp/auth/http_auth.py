"""Bearer token authentication middleware for HTTP/SSE MCP transports."""

import os
import secrets
from typing import Iterable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from linkedin_mcp.config import config


def get_or_create_http_token() -> str:
    """Return configured Bearer token or generate/persist one in ~/.linkedin_mcp/auth_token."""
    if config.mcp_auth_token:
        return config.mcp_auth_token

    token_file = config.auth_token_file
    if token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
        if token:
            return token

    token_file.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    token_file.write_text(token, encoding="utf-8")
    try:
        os.chmod(token_file, 0o600)
    except OSError:
        pass
    return token


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Require a valid Bearer token (Authorization header or ?token=) on MCP endpoints."""

    def __init__(
        self,
        app,
        token: str,
        public_paths: Optional[Iterable[str]] = None,
    ) -> None:
        super().__init__(app)
        self._token = token
        self._public_paths = set(public_paths or ["/"])

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in self._public_paths:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        provided: Optional[str] = None
        if auth_header.lower().startswith("bearer "):
            provided = auth_header[7:].strip()
        elif "token" in request.query_params:
            provided = request.query_params.get("token", "").strip()

        if not provided or not secrets.compare_digest(provided, self._token):
            return JSONResponse(
                {
                    "error": "UNAUTHORIZED",
                    "message": "Missing or invalid Bearer token. Supply 'Authorization: Bearer <token>' or '?token=<token>'.",
                },
                status_code=401,
            )

        return await call_next(request)
