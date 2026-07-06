"""Double-submit cookie CSRF protection middleware.

On every request, ensures a ``csrf_token`` cookie exists (set if absent).
For mutating methods (POST/PUT/DELETE/PATCH) the ``X-CSRF-Token`` request
header must match the cookie value, otherwise a 403 is returned.

Exemptions:
  * Safe methods (GET / HEAD / OPTIONS) are never validated.
  * ``/api/v1/callbacks/tito`` is exempt (machine-to-machine webhook).
  * ``/api/v1/users/login`` is exempt (pre-authentication).
"""

import secrets

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
TOKEN_LENGTH = 32  # 32 bytes → 64 hex chars

# Paths that are exempt from CSRF validation (no header needed).
_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/api/v1/callbacks/tito",
    "/api/v1/users/login",
)

# HTTP methods that require CSRF validation.
_MUTATING_METHODS: frozenset[str] = frozenset({"POST", "PUT", "DELETE", "PATCH"})


def _generate_token() -> str:
    return secrets.token_hex(TOKEN_LENGTH)


def _is_exempt(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES)


class CsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # --- Ensure a CSRF token cookie exists --------------------------------
        existing_token = request.cookies.get(CSRF_COOKIE_NAME)
        token = existing_token or _generate_token()

        # --- Validate on mutating methods ------------------------------------
        if request.method in _MUTATING_METHODS and not _is_exempt(request.url.path):
            header_token = request.headers.get(CSRF_HEADER_NAME)
            if not header_token or not secrets.compare_digest(header_token, token):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token missing or invalid"},
                )

        # --- Call downstream --------------------------------------------------
        response: Response = await call_next(request)

        # --- Set / refresh the cookie ----------------------------------------
        if not existing_token:
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=token,
                samesite="lax",
                httponly=False,
                secure=settings.environment == "production",
                max_age=86400,  # 24 h
            )

        return response
