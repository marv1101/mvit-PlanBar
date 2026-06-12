"""Unit tests for JWT token blacklist functionality."""

from datetime import datetime, timedelta, timezone

from app.core.auth import (
    clean_expired_revoked_tokens,
    create_access_token,
    create_refresh_token,
    is_token_revoked,
    revoke_token,
    verify_token,
)
from app.db.models.revoked_token import RevokedToken


class TestTokenBlacklist:
    def test_token_contains_jti_and_type(self):
        token = create_access_token(subject="1")
        payload = verify_token(token)
        assert "jti" in payload
        assert payload["type"] == "access"

        token = create_refresh_token(subject="1")
        payload = verify_token(token)
        assert "jti" in payload
        assert payload["type"] == "refresh"

    def test_revoke_token(self, db_session):
        token = create_access_token(subject="1")
        payload = verify_token(token)
        jti = payload["jti"]
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        revoke_token(jti, "access", 1, exp, db_session)

        revoked = db_session.query(RevokedToken).filter(RevokedToken.jti == jti).first()
        assert revoked is not None
        assert revoked.jti == jti
        assert revoked.token_type == "access"
        assert revoked.user_id == 1

    def test_is_token_revoked_detects_revoked(self, db_session):
        token = create_access_token(subject="1")
        payload = verify_token(token)
        jti = payload["jti"]
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        assert not is_token_revoked(jti, db_session)
        revoke_token(jti, "access", 1, exp, db_session)
        assert is_token_revoked(jti, db_session)

    def test_clean_expired_revoked_tokens(self, db_session):
        db_session.query(RevokedToken).delete()
        db_session.commit()

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        future = datetime.now(timezone.utc) + timedelta(hours=1)

        revoke_token("expired-jti-1", "access", 1, past, db_session)
        revoke_token("expired-jti-2", "refresh", 1, past, db_session)
        revoke_token("valid-jti", "access", 1, future, db_session)

        count = clean_expired_revoked_tokens(db_session)

        assert count == 2
        assert db_session.query(RevokedToken).count() == 1
        assert db_session.query(RevokedToken).filter(RevokedToken.jti == "valid-jti").first() is not None

    def test_legacy_token_without_jti(self, db_session):
        assert not is_token_revoked(None, db_session)
