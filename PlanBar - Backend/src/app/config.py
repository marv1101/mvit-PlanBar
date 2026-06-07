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
    cors_allow_methods: str = Field("GET,POST,PUT,DELETE,PATCH,OPTIONS")
    cors_allow_headers: str = Field("Authorization,Content-Type,Accept")
    tito_api_key: str | None = Field(None)
    log_level: str = Field("INFO")
    environment: str = Field("development")
    timezone: str = Field("UTC")

    @property
    def cookie_secure(self) -> bool:
        """True for non-development environments (HTTPS required)."""
        return self.environment not in ("development", "test")

    @property
    def is_production(self) -> bool:
        """True for production, demo, or staging environments."""
        return self.environment in ("production", "demo", "staging")


settings = Settings()
