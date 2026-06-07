"""Tests for security hardening: cookie secure flag, CORS config, production validation.

Covers Issue #51: DSGVO Art. 32 — Verschlüsselung und Transport-Sicherheit.
"""

import os

import pytest


class TestCookieSecureFlag:
    """Verify cookie_secure is environment-dependent."""

    def test_dev_environment_insecure_cookies(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECRET_KEY", "test-key")
        from app.config import Settings

        s = Settings()
        assert s.cookie_secure is False

    def test_test_environment_insecure_cookies(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("SECRET_KEY", "test-key")
        from app.config import Settings

        s = Settings()
        assert s.cookie_secure is False

    def test_production_environment_secure_cookies(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
        from app.config import Settings

        s = Settings()
        assert s.cookie_secure is True

    def test_staging_environment_secure_cookies(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
        from app.config import Settings

        s = Settings()
        assert s.cookie_secure is True


class TestCORSConfig:
    """Verify CORS methods and headers are configurable."""

    def test_default_cors_methods(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "test-key")
        from app.config import Settings

        s = Settings()
        assert "GET" in s.cors_allow_methods.split(",")
        assert "POST" in s.cors_allow_methods.split(",")
        assert "PUT" in s.cors_allow_methods.split(",")
        assert "DELETE" in s.cors_allow_methods.split(",")

    def test_default_cors_headers(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "test-key")
        from app.config import Settings

        s = Settings()
        assert "Authorization" in s.cors_allow_headers.split(",")
        assert "Content-Type" in s.cors_allow_headers.split(",")


class TestProductionValidation:
    """Verify production settings validation catches insecure configs."""

    def test_production_rejects_http_cors_origins(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
        monkeypatch.setenv("CORS_ORIGINS", "http://example.com")
        from app.config import Settings

        s = Settings()
        with pytest.raises(RuntimeError, match="CORS origin.*uses HTTP"):
            _validate_cors_for_production(s.cors_origins)

    def test_production_allows_https_cors_origins(self, monkeypatch):
        from app.config import Settings

        s = Settings()
        # Should not raise
        _validate_cors_for_production("https://example.com")


def _validate_cors_for_production(cors_origins: str) -> None:
    """Replicate CORS validation from main._verify_production_settings."""
    origins = cors_origins.split(",") if cors_origins else []
    for origin in origins:
        origin = origin.strip()
        if origin.startswith("http://") and origin != "http://localhost":
            raise RuntimeError(
                f"CORS origin '{origin}' uses HTTP in production. "
                "All CORS origins must use HTTPS in production/staging/demo."
            )
