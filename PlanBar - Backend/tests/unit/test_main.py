"""Tests for app.main module — focusing on security of seed function."""

from unittest.mock import patch


class TestSeedInitialUsers:
    """Verify seed_initial_users never leaks plaintext passwords via logger."""

    def test_seed_does_not_log_passwords(self, db_session):
        """The seed function must NOT log plaintext passwords via logger.info.

        Previously it logged:
            logger.info("Initial-Passwort fuer admin@mphion.de: %s", admin_password)
        This is a security issue because passwords appear in container logs,
        log aggregators, and any monitoring that reads stdout/stderr.
        """
        from app.db.models.user import User
        from app.main import seed_initial_users

        # Remove existing seed users so the seeding code path actually runs
        db_session.query(User).filter(
            User.email.in_(["admin@mphion.de", "testuser@mphion.de"])
        ).delete(synchronize_session=False)
        db_session.commit()

        with patch("app.main.logger") as mock_logger:
            seed_initial_users()

        # Collect all strings passed to logger.info
        logged_strings = []
        for c in mock_logger.info.call_args_list:
            for arg in c.args:
                logged_strings.append(str(arg))

        # Assert no password content leaked through logging
        for msg in logged_strings:
            assert "Passwort" not in msg, (
                f"Password leaked via logger.info: {msg}"
            )
            assert "password" not in msg.lower(), (
                f"Password leaked via logger.info: {msg}"
            )
            # Check for the old pattern "Initial-Passwort fuer <email>: <pw>"
            assert "Initial-Passwort" not in msg, (
                f"Password pattern leaked via logger.info: {msg}"
            )

    def test_seed_creates_users(self, db_session):
        """Verify seed_initial_users still creates users properly."""
        from app.db.models.user import User
        from app.main import seed_initial_users

        # Remove existing seed users
        db_session.query(User).filter(
            User.email.in_(["admin@mphion.de", "testuser@mphion.de"])
        ).delete(synchronize_session=False)
        db_session.commit()

        seed_initial_users()

        admin = db_session.query(User).filter(User.email == "admin@mphion.de").first()
        testuser = db_session.query(User).filter(User.email == "testuser@mphion.de").first()

        assert admin is not None, "admin@mphion.de should be created by seed"
        assert testuser is not None, "testuser@mphion.de should be created by seed"
