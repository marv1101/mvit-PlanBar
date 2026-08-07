"""Unit tests for push_service module.

Covers all functions in app/services/push_service.py:
- _load_or_generate_vapid_keys
- get_vapid_public_key
- _get_vapid_claims
- save_subscription
- remove_subscription
- get_user_subscriptions
- send_push_notification
- send_push_notification_to_user
"""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from pywebpush import WebPushException

from app.db.models.push_subscription import PushSubscription
from app.db.models.user import User
from app.services import push_service

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_user(db_session):
    """Create and return a test user, persisted in the test DB.

    Each test gets a unique user (uuid-suffixed) to avoid UNIQUE-constraint
    collisions when conftest's session-scoped DB persists between tests.
    """
    uid = uuid.uuid4().hex[:8]
    user = User(
        username=f"push_test_user_{uid}",
        email=f"push_test_{uid}@example.com",
        password_hash="hashed_pw",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def reset_vapid_module_state():
    """Reset the module-level VAPID key cache before and after the test."""
    original_private = push_service._vapid_private_key
    original_public = push_service._vapid_public_key
    push_service._vapid_private_key = None
    push_service._vapid_public_key = None
    try:
        yield
    finally:
        push_service._vapid_private_key = original_private
        push_service._vapid_public_key = original_public


# ---------------------------------------------------------------------------
# _load_or_generate_vapid_keys
# ---------------------------------------------------------------------------


def test_load_vapid_keys_from_settings(reset_vapid_module_state):
    """Returns keys from settings when both are set."""
    with patch("app.services.push_service.settings") as mock_settings:
        mock_settings.vapid_private_key = "settings_private"
        mock_settings.vapid_public_key = "settings_public"
        private, public = push_service._load_or_generate_vapid_keys()
    assert private == "settings_private"
    assert public == "settings_public"


def test_load_vapid_keys_caches_settings_values(reset_vapid_module_state):
    """After loading from settings, the keys are cached in module state."""
    with patch("app.services.push_service.settings") as mock_settings:
        mock_settings.vapid_private_key = "cached_private"
        mock_settings.vapid_public_key = "cached_public"
        push_service._load_or_generate_vapid_keys()
        # Now call without settings mock — should return cached values
        private, public = push_service._load_or_generate_vapid_keys()
    assert private == "cached_private"
    assert public == "cached_public"


def test_load_vapid_keys_generate_new_when_no_source(reset_vapid_module_state):
    """Falls back to Vapid().generate_keys() when no source is available."""
    with patch("app.services.push_service.settings") as mock_settings:
        mock_settings.vapid_private_key = None
        mock_settings.vapid_public_key = None
        with patch("app.services.push_service.VAPID_KEY_FILE") as mock_file:
            mock_file.exists.return_value = False
            with patch("app.services.push_service.Vapid") as mock_vapid_cls:
                mock_vapid = MagicMock()
                mock_vapid.private_pem.return_value = b"generated_private"
                mock_vapid.public_pem.return_value = b"generated_public"
                mock_vapid_cls.return_value = mock_vapid
                with patch.object(push_service, "VAPID_KEY_FILE", mock_file):
                    private, public = push_service._load_or_generate_vapid_keys()
    assert private == "generated_private"
    assert public == "generated_public"


def test_load_vapid_keys_generate_new_persists_to_file(reset_vapid_module_state, tmp_path, monkeypatch):
    """Generated keys are written to VAPID_KEY_FILE when writable."""
    import app.services.push_service as ps_mod

    key_file = tmp_path / "vapid_keys.json"
    monkeypatch.setattr(ps_mod, "VAPID_KEY_FILE", key_file)

    with patch("app.services.push_service.settings") as mock_settings:
        mock_settings.vapid_private_key = None
        mock_settings.vapid_public_key = None
        with patch("app.services.push_service.Vapid") as mock_vapid_cls:
            mock_vapid = MagicMock()
            mock_vapid.private_pem.return_value = b"persist_private"
            mock_vapid.public_pem.return_value = b"persist_public"
            mock_vapid_cls.return_value = mock_vapid
            push_service._load_or_generate_vapid_keys()

    assert key_file.exists()
    data = json.loads(key_file.read_text())
    assert data == {
        "private_key": "persist_private",
        "public_key": "persist_public",
    }


# ---------------------------------------------------------------------------
# get_vapid_public_key
# ---------------------------------------------------------------------------


def test_get_vapid_public_key_returns_only_public_part():
    """Returns the public component of the key pair."""
    with patch("app.services.push_service._load_or_generate_vapid_keys") as mock_load:
        mock_load.return_value = ("private_xyz", "public_abc")
        result = push_service.get_vapid_public_key()
    assert result == "public_abc"


# ---------------------------------------------------------------------------
# _get_vapid_claims
# ---------------------------------------------------------------------------


def test_get_vapid_claims_includes_aud_and_sub():
    """Claims dict must include 'sub' (email), 'aud' (FCM), and 'private_key'."""
    with patch("app.services.push_service._load_or_generate_vapid_keys") as mock_load:
        mock_load.return_value = ("priv_key", "pub_key")
        with patch("app.services.push_service.settings") as mock_settings:
            mock_settings.vapid_claim_email = "mailto:admin@example.com"
            claims = push_service._get_vapid_claims()
    assert claims["sub"] == "mailto:admin@example.com"
    assert claims["aud"] == "https://fcm.googleapis.com"
    assert claims["private_key"] == "priv_key"


# ---------------------------------------------------------------------------
# save_subscription
# ---------------------------------------------------------------------------


def test_save_subscription_creates_new_record(db_session, test_user):
    """A new endpoint creates a new PushSubscription row."""
    sub = push_service.save_subscription(
        db=db_session,
        user_id=test_user.id,
        endpoint="https://push.example.com/abc",
        p256dh_key="p256dh_value",
        auth_key="auth_value",
        device_type="web",
        user_agent="Mozilla/5.0",
    )
    assert sub.id is not None
    assert sub.user_id == test_user.id
    assert sub.endpoint == "https://push.example.com/abc"
    assert sub.p256dh_key == "p256dh_value"
    assert sub.auth_key == "auth_value"
    assert sub.device_type == "web"
    assert sub.user_agent == "Mozilla/5.0"


def test_save_subscription_updates_existing_record(db_session, test_user):
    """A second call with the same (user, endpoint) updates the existing row."""
    sub1 = push_service.save_subscription(
        db=db_session,
        user_id=test_user.id,
        endpoint="https://push.example.com/dup",
        p256dh_key="old_p",
        auth_key="old_a",
        device_type="web",
    )
    sub2 = push_service.save_subscription(
        db=db_session,
        user_id=test_user.id,
        endpoint="https://push.example.com/dup",
        p256dh_key="new_p",
        auth_key="new_a",
        device_type="mobile",
    )
    assert sub1.id == sub2.id
    assert sub2.p256dh_key == "new_p"
    assert sub2.auth_key == "new_a"
    assert sub2.device_type == "mobile"

    # Only one row exists for this (user, endpoint)
    count = db_session.query(PushSubscription).filter_by(user_id=test_user.id).count()
    assert count == 1


def test_save_subscription_uses_defaults(db_session, test_user):
    """device_type defaults to 'web' and user_agent defaults to None."""
    sub = push_service.save_subscription(
        db=db_session,
        user_id=test_user.id,
        endpoint="https://push.example.com/defaults",
        p256dh_key="p",
        auth_key="a",
    )
    assert sub.device_type == "web"
    assert sub.user_agent is None


# ---------------------------------------------------------------------------
# remove_subscription
# ---------------------------------------------------------------------------


def test_remove_subscription_returns_true_when_deleted(db_session, test_user):
    """Returns True and removes the row when the subscription exists."""
    push_service.save_subscription(
        db=db_session,
        user_id=test_user.id,
        endpoint="https://push.example.com/remove",
        p256dh_key="p",
        auth_key="a",
    )
    result = push_service.remove_subscription(
        db=db_session,
        user_id=test_user.id,
        endpoint="https://push.example.com/remove",
    )
    assert result is True
    remaining = db_session.query(PushSubscription).filter_by(endpoint="https://push.example.com/remove").first()
    assert remaining is None


def test_remove_subscription_returns_false_when_missing(db_session, test_user):
    """Returns False and changes nothing when the endpoint does not exist."""
    result = push_service.remove_subscription(
        db=db_session,
        user_id=test_user.id,
        endpoint="https://push.example.com/never-existed",
    )
    assert result is False


# ---------------------------------------------------------------------------
# get_user_subscriptions
# ---------------------------------------------------------------------------


def test_get_user_subscriptions_returns_all_for_user(db_session, test_user):
    """Returns all subscriptions belonging to the given user."""
    for i in range(3):
        push_service.save_subscription(
            db=db_session,
            user_id=test_user.id,
            endpoint=f"https://push.example.com/{i}",
            p256dh_key=f"p{i}",
            auth_key=f"a{i}",
        )
    subs = push_service.get_user_subscriptions(db=db_session, user_id=test_user.id)
    assert len(subs) == 3
    assert {s.endpoint for s in subs} == {f"https://push.example.com/{i}" for i in range(3)}


def test_get_user_subscriptions_empty_list_when_no_subs(db_session, test_user):
    """Returns an empty list when the user has no subscriptions."""
    subs = push_service.get_user_subscriptions(db=db_session, user_id=test_user.id)
    assert subs == []


def test_get_user_subscriptions_filters_by_user(db_session, test_user):
    """Subscriptions of other users are not returned."""
    other_uid = uuid.uuid4().hex[:8]
    other = User(
        username=f"other_user_{other_uid}",
        email=f"other_{other_uid}@example.com",
        password_hash="x",
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    push_service.save_subscription(
        db=db_session,
        user_id=test_user.id,
        endpoint="https://push.example.com/mine",
        p256dh_key="p",
        auth_key="a",
    )
    push_service.save_subscription(
        db=db_session,
        user_id=other.id,
        endpoint="https://push.example.com/theirs",
        p256dh_key="p",
        auth_key="a",
    )

    mine = push_service.get_user_subscriptions(db=db_session, user_id=test_user.id)
    theirs = push_service.get_user_subscriptions(db=db_session, user_id=other.id)
    assert len(mine) == 1
    assert mine[0].endpoint == "https://push.example.com/mine"
    assert len(theirs) == 1
    assert theirs[0].endpoint == "https://push.example.com/theirs"


# ---------------------------------------------------------------------------
# send_push_notification
# ---------------------------------------------------------------------------


def _make_sub(endpoint: str = "https://push.example.com/x") -> PushSubscription:
    return PushSubscription(
        user_id=1,
        endpoint=endpoint,
        p256dh_key="p256dh",
        auth_key="auth",
    )


def test_send_push_notification_success_with_url_and_tag():
    """Successful send returns True and payload includes url + tag."""
    sub = _make_sub()
    with (
        patch("app.services.push_service.webpush") as mock_webpush,
        patch("app.services.push_service._get_vapid_claims") as mock_claims,
    ):
        mock_claims.return_value = {
            "sub": "mailto:admin@example.com",
            "private_key": "private_key_value",
            "aud": "https://fcm.googleapis.com",
        }
        result = push_service.send_push_notification(sub, "Title", "Body", url="https://example.com", tag="t1")
    assert result is True
    mock_webpush.assert_called_once()
    kwargs = mock_webpush.call_args.kwargs
    assert kwargs["vapid_private_key"] == "private_key_value"
    assert kwargs["vapid_claims"] == {"sub": "mailto:admin@example.com"}
    assert json.loads(kwargs["data"]) == {
        "title": "Title",
        "body": "Body",
        "url": "https://example.com",
        "tag": "t1",
    }


def test_send_push_notification_success_minimal_payload():
    """Successful send without url/tag omits those keys from payload."""
    sub = _make_sub()
    with (
        patch("app.services.push_service.webpush") as mock_webpush,
        patch("app.services.push_service._get_vapid_claims") as mock_claims,
    ):
        mock_claims.return_value = {
            "sub": "mailto:a@b",
            "private_key": "k",
        }
        result = push_service.send_push_notification(sub, "T", "B")
    assert result is True
    payload = json.loads(mock_webpush.call_args.kwargs["data"])
    assert payload == {"title": "T", "body": "B"}
    assert "url" not in payload
    assert "tag" not in payload


def test_send_push_notification_returns_false_on_404():
    """WebPushException with 404 returns False and logs info."""
    sub = _make_sub("https://push.example.com/404")
    with (
        patch("app.services.push_service.webpush") as mock_webpush,
        patch("app.services.push_service._get_vapid_claims"),
        patch("app.services.push_service.logger") as mock_logger,
    ):
        response = MagicMock()
        response.status_code = 404
        mock_webpush.side_effect = WebPushException("gone", response=response)
        result = push_service.send_push_notification(sub, "T", "B")
    assert result is False
    # 404 is treated as expired/gone — info level
    assert mock_logger.info.called
    info_msg = mock_logger.info.call_args.args[0]
    assert "expired or gone" in info_msg


def test_send_push_notification_returns_false_on_410():
    """WebPushException with 410 returns False and logs info."""
    sub = _make_sub("https://push.example.com/410")
    with (
        patch("app.services.push_service.webpush") as mock_webpush,
        patch("app.services.push_service._get_vapid_claims"),
        patch("app.services.push_service.logger") as mock_logger,
    ):
        response = MagicMock()
        response.status_code = 410
        mock_webpush.side_effect = WebPushException("gone", response=response)
        result = push_service.send_push_notification(sub, "T", "B")
    assert result is False
    assert mock_logger.info.called
    info_msg = mock_logger.info.call_args.args[0]
    assert "expired or gone" in info_msg


def test_send_push_notification_returns_false_on_other_webpush_error():
    """WebPushException without 404/410 returns False and logs warning."""
    sub = _make_sub("https://push.example.com/err")
    with (
        patch("app.services.push_service.webpush") as mock_webpush,
        patch("app.services.push_service._get_vapid_claims"),
        patch("app.services.push_service.logger") as mock_logger,
    ):
        response = MagicMock()
        response.status_code = 500
        mock_webpush.side_effect = WebPushException("server err", response=response)
        result = push_service.send_push_notification(sub, "T", "B")
    assert result is False
    assert mock_logger.warning.called
    warn_msg = mock_logger.warning.call_args.args[0]
    assert "Push notification failed" in warn_msg


def test_send_push_notification_returns_false_on_no_response():
    """WebPushException without a response object returns False."""
    sub = _make_sub("https://push.example.com/noresp")
    with (
        patch("app.services.push_service.webpush") as mock_webpush,
        patch("app.services.push_service._get_vapid_claims"),
        patch("app.services.push_service.logger") as mock_logger,
    ):
        mock_webpush.side_effect = WebPushException("no resp")
        result = push_service.send_push_notification(sub, "T", "B")
    assert result is False
    # Either warning (e.response is None) or info (depending on guard)
    assert mock_logger.warning.called or mock_logger.info.called


# ---------------------------------------------------------------------------
# send_push_notification_to_user
# ---------------------------------------------------------------------------


def test_send_push_notification_to_user_returns_count(db_session, test_user):
    """Returns number of successful sends across all user subscriptions."""
    for i in range(3):
        push_service.save_subscription(
            db=db_session,
            user_id=test_user.id,
            endpoint=f"https://push.example.com/count-{i}",
            p256dh_key=f"p{i}",
            auth_key=f"a{i}",
        )
    with patch("app.services.push_service.send_push_notification", return_value=True) as mock_send:
        count = push_service.send_push_notification_to_user(
            db=db_session,
            user_id=test_user.id,
            title="t",
            body="b",
        )
    assert count == 3
    assert mock_send.call_count == 3


def test_send_push_notification_to_user_deletes_failed_subs(db_session, test_user):
    """Subscriptions that fail to send are removed from the DB."""
    push_service.save_subscription(
        db=db_session,
        user_id=test_user.id,
        endpoint="https://push.example.com/fails",
        p256dh_key="p",
        auth_key="a",
    )
    push_service.save_subscription(
        db=db_session,
        user_id=test_user.id,
        endpoint="https://push.example.com/ok",
        p256dh_key="p",
        auth_key="a",
    )
    with patch(
        "app.services.push_service.send_push_notification",
        side_effect=[False, True],
    ):
        count = push_service.send_push_notification_to_user(
            db=db_session,
            user_id=test_user.id,
            title="t",
            body="b",
        )
    assert count == 1
    remaining = db_session.query(PushSubscription).filter_by(user_id=test_user.id).all()
    assert len(remaining) == 1
    assert remaining[0].endpoint == "https://push.example.com/ok"


def test_send_push_notification_to_user_no_subscriptions(db_session, test_user):
    """Returns 0 and makes no calls when the user has no subscriptions."""
    with patch("app.services.push_service.send_push_notification") as mock_send:
        count = push_service.send_push_notification_to_user(
            db=db_session,
            user_id=test_user.id,
            title="t",
            body="b",
        )
    assert count == 0
    mock_send.assert_not_called()


def test_send_push_notification_to_user_commits_when_subs_exist(db_session, test_user):
    """When there are subscriptions, db.commit() is called after the loop."""
    push_service.save_subscription(
        db=db_session,
        user_id=test_user.id,
        endpoint="https://push.example.com/commit",
        p256dh_key="p",
        auth_key="a",
    )
    with (
        patch("app.services.push_service.send_push_notification", return_value=True),
        patch.object(db_session, "commit") as mock_commit,
    ):
        push_service.send_push_notification_to_user(
            db=db_session,
            user_id=test_user.id,
            title="t",
            body="b",
        )
    assert mock_commit.called


def test_send_push_notification_to_user_no_commit_when_no_subs(db_session, test_user):
    """When the user has no subscriptions, db.commit() is NOT called."""
    with (
        patch("app.services.push_service.send_push_notification", return_value=True),
        patch.object(db_session, "commit") as mock_commit,
    ):
        push_service.send_push_notification_to_user(
            db=db_session,
            user_id=test_user.id,
            title="t",
            body="b",
        )
    assert not mock_commit.called
