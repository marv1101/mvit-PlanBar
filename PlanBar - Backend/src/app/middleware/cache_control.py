import logging
import re
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

API_CACHE_PATTERNS = [
    re.compile(r"^/api/v1/employees/?$"),
    re.compile(r"^/api/v1/roles/?$"),
    re.compile(r"^/api/v1/schedules/?$"),
    re.compile(r"^/api/v1/requests/?$"),
    re.compile(r"^/api/v1/sync/"),
]

EXCLUDE_PATTERNS = [
    re.compile(r"^/api/v1/users/(login|logout|refresh-token)"),
    re.compile(r"^/api/v1/notifications"),
    re.compile(r"^/api/v1/pinboard"),
]


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Add cache-control headers to API GET responses."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if request.method != "GET":
            return response

        path = request.url.path

        for exclude in EXCLUDE_PATTERNS:
            if exclude.match(path):
                return response

        should_cache = False
        for pattern in API_CACHE_PATTERNS:
            if pattern.match(path):
                should_cache = True
                break

        if not should_cache:
            return response

        if response.status_code < 200 or response.status_code >= 400:
            return response

        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        response.headers["Last-Modified"] = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")

        return response
