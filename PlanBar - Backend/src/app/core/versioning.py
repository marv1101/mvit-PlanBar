import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import Response
from pydantic import BaseModel


def compute_etag(data: Any) -> str:
    """Compute an ETag hash for a given data payload."""
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    elif hasattr(data, "__dict__"):
        data = data.__dict__
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def add_cache_headers(response: Response, etag: str | None = None, last_modified: datetime | None = None) -> None:
    """Add cache-control, ETag and Last-Modified headers to a response."""
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    if etag:
        response.headers["ETag"] = f'"{etag}"'
    if last_modified:
        response.headers["Last-Modified"] = last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")


def check_if_none_match(if_none_match: str | None, etag: str) -> bool:
    """Return True if the client's cached version matches (304 Not Modified)."""
    if not if_none_match:
        return False
    etag_value = if_none_match.strip().strip('"').strip("W/")
    return etag_value == etag


def check_if_modified_since(if_modified_since: str | None, last_modified: datetime) -> bool:
    """Return True if the resource hasn't been modified since."""
    if not if_modified_since:
        return False
    try:
        since = datetime.strptime(if_modified_since, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=UTC)
        return last_modified <= since
    except (ValueError, TypeError):
        return False


class ConflictError(Exception):
    """Raised when a resource has been modified by another party."""

    def __init__(self, message: str = "Conflict: resource was modified by another user"):
        self.message = message
        super().__init__(self.message)


def detect_conflict(
    stored_updated_at: datetime | None,
    if_match: str | None,
    current_etag: str,
    tolerance_seconds: int = 5,
) -> bool:
    """Detect if a conflict exists based on If-Match header or time-based heuristic."""
    if if_match:
        expected = if_match.strip().strip('"').strip("W/")
        if expected != current_etag:
            raise ConflictError("Resource was modified by another user. Please refresh and try again.")
        return False

    if stored_updated_at:
        age = (datetime.now(UTC) - stored_updated_at.replace(tzinfo=UTC)).total_seconds()
        if age > tolerance_seconds:
            raise ConflictError("Resource may have been modified. Please refresh and try again.")

    return False


# ---------------------------------------------------------------------------
# Convenience helpers for the GET/PUT ETag pattern
# ---------------------------------------------------------------------------


def resource_etag_dict(model, *fields: str) -> dict:
    """Build the dict used to compute an ETag for *model*.

    *fields* are attribute names read from *model*.  ``updated_at`` is
    always included automatically.
    """
    d = {f: str(getattr(model, f)) for f in fields}
    d["updated_at"] = str(model.updated_at)
    return d


def set_etag_header(response: Response, model, *fields: str) -> None:
    """Compute and set the ETag + Cache-Control headers on *response* (GET)."""
    etag = compute_etag(resource_etag_dict(model, *fields))
    add_cache_headers(response, etag=etag, last_modified=model.updated_at)


def check_etag_conflict(model, if_match: str | None, *fields: str) -> None:
    """Raise ``ConflictError`` if the client's ETag doesn't match (PUT pre-check)."""
    etag = compute_etag(resource_etag_dict(model, *fields))
    detect_conflict(model.updated_at, if_match, etag)


def set_etag_response(response: Response, model, *fields: str) -> str:
    """Set the new ETag after a successful update (PUT post-check).  Returns the ETag."""
    etag = compute_etag(resource_etag_dict(model, *fields))
    add_cache_headers(response, etag=etag)
    return etag
