from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        response: Response = await call_next(request)
        env = settings.environment

        if env in ("production", "demo", "staging"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        if env in ("production", "demo", "staging"):
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self'; "
                "connect-src 'self'"
            )
        else:
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-eval' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self'; "
                "connect-src 'self' http://localhost:* ws://localhost:*"
            )

        response.headers["Content-Security-Policy"] = csp
        return response


class HttpsRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if settings.environment in ("production", "demo", "staging"):
            proto = request.headers.get("x-forwarded-proto", "").lower()
            if proto and proto != "https":
                host = request.headers.get("host", "localhost")
                url = f"https://{host}{request.url.path}"
                if request.url.query:
                    url += f"?{request.url.query}"
                return JSONResponse(
                    status_code=426,
                    content={
                        "detail": "Upgrade Required",
                        "message": "This endpoint requires HTTPS. Please reconnect using HTTPS.",
                    },
                )
        return await call_next(request)
