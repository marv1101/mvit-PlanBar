"""Unit tests for password complexity validation."""
import pytest
from pydantic import ValidationError
from app.schemas.user import UserCreate, UserLogin, ChangePasswordRequest


class TestPasswordComplexity:
    """Test password meets complexity requirements: min 8 chars, uppercase, lowercase, digit, special char."""

    def test_valid_password_accepted(self):
        """A password with all requirements should be accepted."""
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="StrongP@ss1"
        )
        assert user.password == "StrongP@ss1"

    def test_too_short_rejected(self):
        """Password shorter than 8 chars should be rejected."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="Sh@1x"
            )

    def test_no_uppercase_rejected(self):
        """Password without uppercase letter should be rejected."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="lowercase@1"
            )

    def test_no_digit_rejected(self):
        """Password without digit should be rejected."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="NoDigit@here"
            )

    def test_no_special_char_rejected(self):
        """Password without special character should be rejected."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="NoSpecial1"
            )

    def test_no_lowercase_rejected(self):
        """Password without lowercase letter should be rejected."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="NOLOWERCASE@1"
            )

    def test_login_schema_allows_weak_password(self):
        """Login schema should allow weak passwords for backward compatibility.

        Users may have old passwords that predate complexity requirements.
        """
        login = UserLogin(
            email="test@example.com",
            password="weakpass"
        )
        assert login.password == "weakpass"

    def test_change_password_schema_enforces_complexity(self):
        """ChangePasswordRequest should enforce complexity on new_password."""
        with pytest.raises(ValidationError):
            ChangePasswordRequest(
                old_password="OldPass@1",
                new_password="weak"
            )
