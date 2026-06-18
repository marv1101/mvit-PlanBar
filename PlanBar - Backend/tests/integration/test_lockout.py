"""Integration tests for account lockout after failed login attempts."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.services.lockout_service import LockoutService


class TestAccountLockout:
    """Test account lockout after 5 failed attempts for 15 minutes."""

    def setup_method(self):
        """Reset lockout service before each test."""
        self.lockout = LockoutService()
        self.lockout._attempts.clear()
        self.lockout._lockouts.clear()

    def test_lockout_after_5_failed_attempts(self):
        """Account should be locked after 5 failed login attempts."""
        email = "test@example.com"

        # First 4 attempts should not lock the account
        for i in range(4):
            assert self.lockout.record_failed_attempt(email) is False
            assert self.lockout.is_locked(email) is False

        # 5th attempt should lock the account
        assert self.lockout.record_failed_attempt(email) is True
        assert self.lockout.is_locked(email) is True

    def test_lockout_resets_after_success(self):
        """Failed attempt counter should reset after successful login."""
        email = "test@example.com"

        # Make 4 failed attempts
        for i in range(4):
            self.lockout.record_failed_attempt(email)

        # Successful login should reset counter
        self.lockout.record_successful_login(email)

        # Should be able to make 4 more failed attempts without lockout
        for i in range(4):
            assert self.lockout.record_failed_attempt(email) is False

        assert self.lockout.is_locked(email) is False

    def test_lockout_expires_after_timeout(self):
        """Lockout should expire after 15 minutes."""
        email = "test@example.com"

        # Trigger lockout
        for i in range(5):
            self.lockout.record_failed_attempt(email)

        assert self.lockout.is_locked(email) is True

        # Mock time advancement - set lockout time to 15 minutes ago
        with patch('app.services.lockout_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now(timezone.utc) + timedelta(minutes=16)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Force re-evaluation of lockout status
            assert self.lockout.is_locked(email) is False

    def test_get_remaining_lockout_time(self):
        """Should return remaining lockout time in seconds."""
        email = "test@example.com"

        # Before lockout, remaining time should be 0
        assert self.lockout.get_remaining_lockout_time(email) == 0

        # Trigger lockout
        for i in range(5):
            self.lockout.record_failed_attempt(email)

        # Should have positive remaining time
        remaining = self.lockout.get_remaining_lockout_time(email)
        assert remaining > 0
        assert remaining <= 900  # 15 minutes = 900 seconds

    def test_failed_attempts_count(self):
        """Should track correct number of failed attempts."""
        email = "test@example.com"

        assert self.lockout.get_failed_attempts_count(email) == 0

        self.lockout.record_failed_attempt(email)
        assert self.lockout.get_failed_attempts_count(email) == 1

        self.lockout.record_failed_attempt(email)
        assert self.lockout.get_failed_attempts_count(email) == 2

    def test_different_accounts_tracked_separately(self):
        """Failed attempts for different accounts should be tracked separately."""
        email1 = "user1@example.com"
        email2 = "user2@example.com"

        # Make 4 failed attempts for user1
        for i in range(4):
            self.lockout.record_failed_attempt(email1)

        # Make 2 failed attempts for user2
        for i in range(2):
            self.lockout.record_failed_attempt(email2)

        # user1 should have 4 attempts, user2 should have 2
        assert self.lockout.get_failed_attempts_count(email1) == 4
        assert self.lockout.get_failed_attempts_count(email2) == 2

        # Neither should be locked yet
        assert self.lockout.is_locked(email1) is False
        assert self.lockout.is_locked(email2) is False
