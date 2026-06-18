"""Account lockout service for tracking failed login attempts.

BSI IT-Grundschutz recommends account lockout after 5-10 failed attempts.
This implementation locks accounts after 5 failed attempts for 15 minutes.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional


class LockoutService:
    """In-memory lockout service tracking failed login attempts per email."""

    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

    def __init__(self):
        # Track failed attempts: {email: {"count": int, "first_attempt": datetime}}
        self._attempts: dict[str, dict] = {}
        # Track lockouts: {email: datetime} (when lockout started)
        self._lockouts: dict[str, datetime] = {}

    def record_failed_attempt(self, email: str) -> bool:
        """
        Record a failed login attempt for the given email.

        Returns True if the account is now locked, False otherwise.
        """
        now = datetime.now(timezone.utc)

        # Check if account is already locked
        if self.is_locked(email):
            return True

        if email not in self._attempts:
            self._attempts[email] = {"count": 1, "first_attempt": now}
        else:
            self._attempts[email]["count"] += 1

        # Check if we should lock the account
        if self._attempts[email]["count"] >= self.MAX_FAILED_ATTEMPTS:
            self._lockouts[email] = now
            return True

        return False

    def is_locked(self, email: str) -> bool:
        """Check if the account is currently locked."""
        if email not in self._lockouts:
            return False

        lockout_time = self._lockouts[email]
        now = datetime.now(timezone.utc)
        lockout_duration = timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)

        if now - lockout_time >= lockout_duration:
            # Lockout has expired
            del self._lockouts[email]
            if email in self._attempts:
                del self._attempts[email]
            return False

        return True

    def record_successful_login(self, email: str) -> None:
        """Reset failed attempt counter after successful login."""
        if email in self._attempts:
            del self._attempts[email]
        if email in self._lockouts:
            del self._lockouts[email]

    def get_failed_attempts_count(self, email: str) -> int:
        """Get the current number of failed attempts for the given email."""
        if email not in self._attempts:
            return 0
        return self._attempts[email]["count"]

    def get_remaining_lockout_time(self, email: str) -> int:
        """
        Get remaining lockout time in seconds.

        Returns 0 if not locked out.
        """
        if not self.is_locked(email):
            return 0

        lockout_time = self._lockouts[email]
        now = datetime.now(timezone.utc)
        lockout_duration = timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
        elapsed = now - lockout_time
        remaining = lockout_duration - elapsed

        return max(0, int(remaining.total_seconds()))


# Singleton instance
lockout_service = LockoutService()
