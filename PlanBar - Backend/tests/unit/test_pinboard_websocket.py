"""Unit tests for the extracted WebSocket helpers from pinboard.websocket_endpoint.

These tests cover the three responsibilities extracted from the 106-line
`websocket_endpoint` function in `app/api/v1/pinboard.py`:

  * `authenticate_websocket` — token, cookie, thread and user checks
  * `handle_websocket_message` — ping / pong / message / unknown dispatch
  * `persist_chat_message`    — DB write + thread updated_at bump

The tests are pure (no real WebSocket), so they run quickly and deterministically.
"""

from __future__ import annotations

import json
import os
import uuid
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_pinbar_ws_unit.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest

from app.api.v1.pinboard_ws import (
    authenticate_websocket,
    handle_websocket_message,
    persist_chat_message,
)
from app.core.auth import create_access_token

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_websocket():
    """Minimal stand-in for fastapi.WebSocket that records send_json calls."""
    ws = MagicMock()
    ws.cookies = {}
    ws.sent = []

    async def _send_json(payload):
        ws.sent.append(payload)

    ws.send_json = _send_json
    return ws


@pytest.fixture
def user(db_session):
    from app.db.models.user import User

    # uuid-suffixed identity dodges UNIQUE collisions across session-scoped SQLite
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"wsuser-{uid}",
        email=f"wsuser-{uid}@test.com",
        password_hash="x",
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def thread(db_session, user):
    from app.db.models.pinboard import PinboardThread

    thread = PinboardThread(title=f"ws-test-{uuid.uuid4().hex[:8]}", author_id=user.id)
    db_session.add(thread)
    db_session.commit()
    db_session.refresh(thread)
    return thread


@pytest.fixture
def valid_token(user):
    return create_access_token(subject=str(user.id))


# ---------------------------------------------------------------------------
# authenticate_websocket
# ---------------------------------------------------------------------------


class TestAuthenticateWebsocket:
    def test_returns_user_when_query_token_valid(self, db_session, user, thread, valid_token):
        result = authenticate_websocket(
            db=db_session,
            thread_id=thread.id,
            query_token=valid_token,
            cookies={},
        )
        assert result is not None
        assert result[0].id == user.id
        assert result[1] == user.id

    def test_returns_user_when_cookie_token_valid(self, db_session, user, thread, valid_token):
        result = authenticate_websocket(
            db=db_session,
            thread_id=thread.id,
            query_token="",
            cookies={"access_token": valid_token},
        )
        assert result is not None
        assert result[0].id == user.id

    def test_returns_none_when_thread_missing(self, db_session, valid_token):
        result = authenticate_websocket(
            db=db_session,
            thread_id=99999,
            query_token=valid_token,
            cookies={},
        )
        assert result is None

    def test_returns_none_when_no_token(self, db_session, thread):
        result = authenticate_websocket(
            db=db_session,
            thread_id=thread.id,
            query_token="",
            cookies={},
        )
        assert result is None

    def test_returns_none_when_token_invalid(self, db_session, thread):
        result = authenticate_websocket(
            db=db_session,
            thread_id=thread.id,
            query_token="not-a-jwt",
            cookies={},
        )
        assert result is None

    def test_returns_none_when_token_has_no_sub(self, db_session, thread):
        # Manually build a token that decodes but lacks "sub"
        with patch("app.api.v1.pinboard_ws.verify_token", return_value={}):
            result = authenticate_websocket(
                db=db_session,
                thread_id=thread.id,
                query_token="any",
                cookies={},
            )
        assert result is None

    def test_returns_none_when_user_not_in_db(self, db_session, thread):
        token = create_access_token(subject="99999")
        result = authenticate_websocket(
            db=db_session,
            thread_id=thread.id,
            query_token=token,
            cookies={},
        )
        assert result is None

    def test_query_token_takes_precedence_over_cookie(self, db_session, user, thread, valid_token):
        # Even if cookie is invalid, a valid query token should work
        result = authenticate_websocket(
            db=db_session,
            thread_id=thread.id,
            query_token=valid_token,
            cookies={"access_token": "garbage"},
        )
        assert result is not None


# ---------------------------------------------------------------------------
# handle_websocket_message
# ---------------------------------------------------------------------------


class TestHandleWebsocketMessage:
    @pytest.mark.asyncio
    async def test_ping_returns_pong(self, fake_websocket):
        await handle_websocket_message(fake_websocket, thread_id=1, user_id=1, raw='{"type":"ping"}')
        assert fake_websocket.sent == [{"type": "pong"}]

    @pytest.mark.asyncio
    async def test_pong_is_silently_consumed(self, fake_websocket):
        await handle_websocket_message(fake_websocket, thread_id=1, user_id=1, raw='{"type":"pong"}')
        assert fake_websocket.sent == []

    @pytest.mark.asyncio
    async def test_unknown_type_returns_error(self, fake_websocket):
        await handle_websocket_message(fake_websocket, thread_id=1, user_id=1, raw='{"type":"wat"}')
        assert fake_websocket.sent == [{"type": "error", "detail": "Unknown message type: wat"}]

    @pytest.mark.asyncio
    async def test_message_with_empty_content_returns_error(self, fake_websocket):
        await handle_websocket_message(
            fake_websocket,
            thread_id=1,
            user_id=1,
            raw=json.dumps({"type": "message", "content": "   "}),
        )
        assert fake_websocket.sent == [{"type": "error", "detail": "Content is required"}]

    @pytest.mark.asyncio
    async def test_message_persists_and_broadcasts(self, fake_websocket):
        broadcast_payloads = []

        async def _broadcast(tid, payload):
            broadcast_payloads.append((tid, payload))

        with (
            patch("app.api.v1.pinboard_ws._do_broadcast", _broadcast),
            patch("app.api.v1.pinboard_ws.SessionLocal") as session_factory,
            patch("app.api.v1.pinboard._message_to_response") as to_response,
        ):
            fake_db = MagicMock()
            fake_thread = MagicMock()
            fake_db.query.return_value.filter.return_value.first.side_effect = [
                fake_thread,
            ]
            fake_db.add = MagicMock()
            fake_db.commit = MagicMock()
            fake_db.refresh = MagicMock()
            fake_db.close = MagicMock()
            session_factory.return_value = fake_db

            fake_message_response = MagicMock()
            fake_message_response.model_dump.return_value = {"id": 42, "content": "hello"}
            to_response.return_value = fake_message_response

            await handle_websocket_message(
                fake_websocket,
                thread_id=1,
                user_id=1,
                raw=json.dumps({"type": "message", "content": "hello"}),
            )

        assert len(broadcast_payloads) == 1
        tid, payload = broadcast_payloads[0]
        assert tid == 1
        assert payload["type"] == "new_message"
        assert payload["message"] == {"id": 42, "content": "hello"}
        fake_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_json_returns_error(self, fake_websocket):
        await handle_websocket_message(fake_websocket, thread_id=1, user_id=1, raw="not json")
        assert fake_websocket.sent == [{"type": "error", "detail": "Invalid JSON"}]


# ---------------------------------------------------------------------------
# persist_chat_message
# ---------------------------------------------------------------------------


class TestPersistChatMessage:
    @pytest.mark.asyncio
    async def test_creates_message_and_bumps_thread(self, db_session, user, thread):
        broadcast_payloads = []

        async def _broadcast(tid, payload):
            broadcast_payloads.append((tid, payload))

        with (
            patch("app.api.v1.pinboard_ws._do_broadcast", _broadcast),
            patch("app.api.v1.pinboard._message_to_response") as to_response,
        ):
            response = MagicMock()
            response.model_dump.return_value = {"id": 1, "content": "hi"}
            to_response.return_value = response

            await persist_chat_message(db_session, thread_id=thread.id, user_id=user.id, content="hi")

        from app.db.models.pinboard import PinboardMessage

        msgs = db_session.query(PinboardMessage).filter_by(thread_id=thread.id).all()
        assert len(msgs) == 1
        assert msgs[0].content == "hi"
        assert msgs[0].author_id == user.id

        db_session.refresh(thread)
        assert thread.updated_at is not None
        assert len(broadcast_payloads) == 1
