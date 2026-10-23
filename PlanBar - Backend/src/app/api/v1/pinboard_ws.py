"""WebSocket helpers extracted from `app.api.v1.pinboard.websocket_endpoint`.

The original endpoint was a 106-line function that mixed four concerns:
thread validation, authentication, connection bookkeeping, and message
parsing/persistence. This module extracts three small, testable helpers:

* :func:`authenticate_websocket` — validates thread + token + user, returns
  ``(user, user_id)`` on success or ``None`` on any failure.
* :func:`handle_websocket_message` — dispatches a single incoming text frame
  (``ping``/``pong``/``message``/unknown) to the appropriate response.
* :func:`persist_chat_message` — performs the DB write for a chat message,
  bumps ``PinboardThread.updated_at``, and broadcasts a ``new_message`` event.

The thin orchestrator :func:`websocket_endpoint` (still defined in
``pinboard.py``) now reads as a sequence of named steps instead of a wall
of nested conditionals.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.core.auth import verify_token
from app.db.database import SessionLocal
from app.db.models.pinboard import PinboardMessage, PinboardThread
from app.db.models.user import User

logger = logging.getLogger(__name__)


def _do_broadcast(thread_id: int, message: dict):
    """Lazy-resolved wrapper around ``app.api.v1.pinboard._broadcast``.

    Importing ``_broadcast`` eagerly would cause a circular import: ``pinboard``
    imports this module to use :func:`handle_websocket_message`, and this
    module imports the broadcast helper from ``pinboard``. Resolving at call
    time keeps the module-level dependency graph acyclic.

    Returns the coroutine so the caller (an async context) can ``await`` it
    without resorting to ``asyncio.ensure_future`` — that helper requires a
    running event loop, which tests and other call-sites may not provide.
    """
    from app.api.v1.pinboard import _broadcast as _pinboard_broadcast

    return _pinboard_broadcast(thread_id, message)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def _extract_token(token: str, cookies: dict[str, str]) -> str:
    """Pick the first non-empty token from the query string or the cookies."""
    if token:
        return token
    return cookies.get("access_token", "")


def _decode_user_id(token: str) -> int | None:
    """Return the user id encoded in the JWT, or ``None`` if invalid."""
    try:
        payload = verify_token(token)
    except (ValueError, Exception):  # noqa: BLE001
        return None
    sub = payload.get("sub") if isinstance(payload, dict) else None
    if sub is None:
        return None
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def authenticate_websocket(
    db: Session,
    thread_id: int,
    query_token: str,
    cookies: dict[str, str],
) -> tuple[User, int] | None:
    """Validate the websocket connection prerequisites.

    Returns a ``(user, user_id)`` tuple when the thread exists, a valid token
    is supplied, and the referenced user is present in the database. Returns
    ``None`` for any failure — the caller is expected to close the socket with
    an appropriate status code and reason based on the failure point.
    """
    thread_exists = db.query(PinboardThread).filter(PinboardThread.id == thread_id).first()
    if not thread_exists:
        logger.warning("WebSocket connection attempted to non-existent thread %s", thread_id)
        return None

    token_str = _extract_token(query_token, cookies)
    if not token_str:
        logger.warning("WebSocket auth failed: no token provided")
        return None

    user_id = _decode_user_id(token_str)
    if user_id is None:
        logger.warning("WebSocket auth failed: invalid token")
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning("WebSocket auth failed: user %s not found in database", user_id)
        return None

    return user, user_id


# ---------------------------------------------------------------------------
# Message dispatch
# ---------------------------------------------------------------------------


async def persist_chat_message(db: Session, thread_id: int, user_id: int, content: str) -> None:
    """Persist a chat message, bump the thread timestamp, and broadcast it.

    This is split out of the dispatch loop so the per-frame logic in
    :func:`handle_websocket_message` stays focused on routing. The function
    owns the ``db`` session's lifecycle: callers must not commit again.

    The function is async because the broadcast step needs an awaitable for
    the underlying :func:`_broadcast` coroutine — running it via
    ``asyncio.ensure_future`` would require a live event loop, which both
    unit tests and ad-hoc callers may not provide.
    """
    message = PinboardMessage(
        thread_id=thread_id,
        author_id=user_id,
        content=content,
    )
    db.add(message)
    thread = db.query(PinboardThread).filter(PinboardThread.id == thread_id).first()
    if thread:
        thread.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(message)

    # Imported lazily to avoid a circular import (broadcast lives in pinboard.py)
    from app.api.v1.pinboard import _message_to_response

    msg_response = _message_to_response(message)
    await _do_broadcast(
        thread_id,
        {
            "type": "new_message",
            "message": msg_response.model_dump(mode="json"),
        },
    )


async def handle_websocket_message(
    websocket: WebSocket,
    thread_id: int,
    user_id: int,
    raw: str,
) -> None:
    """Dispatch a single incoming text frame to the appropriate response.

    Recognised message types:

    * ``ping``  — reply with ``{"type": "pong"}``
    * ``pong``  — silently consumed
    * ``message`` — persist + broadcast (see :func:`persist_chat_message`)
    * anything else — reply with an error describing the unknown type

    Malformed JSON is reported as an error rather than raised so the websocket
    loop can keep running.
    """
    try:
        msg_data = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
        return

    msg_type = msg_data.get("type", "ping")

    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})
        return

    if msg_type == "pong":
        return

    if msg_type == "message":
        content = (msg_data.get("content", "") or "").strip()
        if not content:
            await websocket.send_json({"type": "error", "detail": "Content is required"})
            return

        db = SessionLocal()
        try:
            await persist_chat_message(db, thread_id=thread_id, user_id=user_id, content=content)
        finally:
            db.close()
        return

    await websocket.send_json({"type": "error", "detail": f"Unknown message type: {msg_type}"})


__all__ = [
    "authenticate_websocket",
    "handle_websocket_message",
    "persist_chat_message",
]
