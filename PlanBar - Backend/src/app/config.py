from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field("sqlite:///./planbar.db")
    secret_key: str = Field(...)
    jwt_algorithm: str = Field("HS256")
    access_token_expire_minutes: int = Field(15)
    refresh_token_expire_days: int = Field(7)
    tito_api_url: str = Field("http://localhost:5001")
    backend_callback_url: str = Field("http://localhost:8000")
    cors_origins: str = Field("http://localhost:5173,http://localhost:3000")
    tito_api_key: str | None = Field(None)
    log_level: str = Field("INFO")
    upload_dir: str = Field("./uploads/pinboard")
    environment: str = Field("development")
    timezone: str = Field("UTC")

    vapid_private_key: str | None = Field(None)
    vapid_public_key: str | None = Field(None)
    vapid_claim_email: str = Field("mailto:admin@mphion.de")

    # Security: Public self-registration is disabled by default.
    # When True, POST /api/v1/users creates a new public user (legacy/invite-only
    # onboarding flows). When False (production default), the endpoint returns 403
    # and admins must use POST /api/v1/users/admin-create instead.
    enable_self_registration: bool = Field(False)

    retention_auto_enabled: bool = Field(False)
    retention_cleanup_hour: int = Field(3)


settings = Settings()
