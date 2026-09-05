from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.services.arbzg_rules import (
    MAX_CONSECUTIVE_DAYS,
    MAX_DAILY_HOURS,
    MAX_WEEKLY_HOURS_LAW,
    MIN_FREE_SUNDAYS_PER_YEAR,
    MIN_REST_HOURS,
    NIGHT_WINDOW_END,
    NIGHT_WINDOW_START,
    NIGHT_WORK_MAX_HOURS,
)


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

    # ── ArbZG / TiTO solver parameters ─────────────────────────────────────
    # Sent to the config section of the TiTO job payload so PlanBar and TiTO
    # plan against the SAME rule set. Defaults come from app.services.arbzg_rules
    # (single source of truth for both the validator and the solver config).
    min_rest_time_hours: float = Field(MIN_REST_HOURS)  # § 5 ArbZG
    max_daily_work_hours: float = Field(MAX_DAILY_HOURS)  # § 3 ArbZG
    max_consecutive_days: int = Field(MAX_CONSECUTIVE_DAYS)  # § 3 + § 9 ArbZG
    min_free_sundays_per_year: int = Field(MIN_FREE_SUNDAYS_PER_YEAR)  # § 9 ArbZG
    night_window_start: str = Field(NIGHT_WINDOW_START)  # § 6 ArbZG
    night_window_end: str = Field(NIGHT_WINDOW_END)  # § 6 ArbZG
    night_work_max_hours: float = Field(NIGHT_WORK_MAX_HOURS)  # § 6 ArbZG
    rest_time_shift_workers_hours: float | None = Field(None)  # § 5 Abs. 2a (unused by default)
    max_weekly_hours_law: float = Field(MAX_WEEKLY_HOURS_LAW)  # § 3 S. 2 ArbZG

    # German federal state for state-specific public holidays (§ 9 ArbZG),
    # e.g. "BW", "BY", "BE". None = nationwide holidays only.
    german_state: str | None = Field(None)


settings = Settings()
