from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_size:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large"},
                    )
            except ValueError:
                pass
        return await call_next(request)
