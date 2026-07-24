from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


async def http_error_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


def _sanitize_errors(errors) -> list:
    """Convert non-serializable objects in validation errors to strings."""
    sanitized = []
    for error in errors:
        clean = {}
        for key, value in error.items():
            if key == "ctx" and isinstance(value, dict):
                clean[key] = {k: str(v) for k, v in value.items()}
            else:
                clean[key] = value
        sanitized.append(clean)
    return sanitized


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": _sanitize_errors(exc.errors())}, status_code=422)
