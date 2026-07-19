"""Pydantic-Settings für das Backup-Modul."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated, List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class StorageType(str, Enum):
    LOCAL = "local"
    S3 = "s3"


class BackupConfig(BaseSettings):
    """Konfiguration des Backup-Moduls via Umgebungsvariablen.

    Siehe `Docs/s3-backup-plan.md` Abschnitt 6 für die vollständige Liste.
    """

    model_config = SettingsConfigDict(
        env_prefix="BACKUP_",
        case_sensitive=False,
        extra="ignore",
    )

    storage_type: StorageType = StorageType.LOCAL
    # NoDecode verhindert, dass pydantic-settings den String als JSON parsed.
    tenants: Annotated[List[str], NoDecode] = []
    local_dir: Path = Path("/opt/planbar/backups")

    s3_bucket: str | None = None
    s3_endpoint: str | None = None
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_path_prefix: str = ""

    retention_days: int = 30
    verify_upload: bool = True
    lock_ttl_seconds: int = 300

    db_url_planbar: str | None = None
    db_url_tito: str | None = None
    uploads_dir: Path | None = None
    config_dir: Path | None = None
    include_migrations: bool = True

    @field_validator("tenants", mode="before")
    @classmethod
    def _parse_tenants(cls, value):
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [t.strip() for t in value.split(",") if t.strip()]
        raise ValueError("tenants must be a comma-separated string or a list")

    @field_validator("retention_days")
    @classmethod
    def _validate_retention(cls, value: int) -> int:
        if value < 0:
            raise ValueError("retention_days must be >= 0")
        return value

    @model_validator(mode="after")
    def _validate_s3(self) -> "BackupConfig":
        if self.storage_type is StorageType.S3 and not self.s3_bucket:
            raise ValueError("BACKUP_S3_BUCKET is required when storage_type is s3")
        return self
