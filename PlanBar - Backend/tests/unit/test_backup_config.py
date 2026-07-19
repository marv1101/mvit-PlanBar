"""Tests für `app.backup.config` und `app.backup.exceptions`."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.backup.config import BackupConfig, StorageType
from app.backup.exceptions import BackupError, BackupLockError, BackupNotFoundError


class _Env:
    """Helper um ENV-Variablen temporär zu setzen."""

    def __init__(self, monkeypatch):
        self.monkeypatch = monkeypatch

    def set(self, **kwargs):
        for key, value in kwargs.items():
            if value is None:
                self.monkeypatch.delenv(key, raising=False)
            else:
                self.monkeypatch.setenv(key, value)


def _make_config(env: dict, monkeypatch):
    helper = _Env(monkeypatch)
    helper.set(
        **{
            k: None
            for k in (
                "BACKUP_STORAGE_TYPE",
                "BACKUP_TENANTS",
                "BACKUP_LOCAL_DIR",
                "BACKUP_S3_BUCKET",
                "BACKUP_S3_ENDPOINT",
                "BACKUP_S3_REGION",
                "BACKUP_S3_ACCESS_KEY_ID",
                "BACKUP_S3_SECRET_ACCESS_KEY",
                "BACKUP_S3_PATH_PREFIX",
                "BACKUP_RETENTION_DAYS",
                "BACKUP_VERIFY_UPLOAD",
                "BACKUP_LOCK_TTL_SECONDS",
                "BACKUP_DB_URL_PLANBAR",
                "BACKUP_DB_URL_TITO",
                "BACKUP_UPLOADS_DIR",
                "BACKUP_CONFIG_DIR",
                "BACKUP_INCLUDE_MIGRATIONS",
            )
        }
    )
    helper.set(**env)
    return BackupConfig()


def test_config_defaults(monkeypatch):
    cfg = _make_config({}, monkeypatch)
    assert cfg.storage_type is StorageType.LOCAL
    assert cfg.tenants == []
    assert cfg.local_dir == Path("/opt/planbar/backups")
    assert cfg.s3_bucket is None
    assert cfg.s3_endpoint is None
    assert cfg.s3_region is None
    assert cfg.s3_access_key_id is None
    assert cfg.s3_secret_access_key is None
    assert cfg.s3_path_prefix == ""
    assert cfg.retention_days == 30
    assert cfg.verify_upload is True
    assert cfg.lock_ttl_seconds == 300
    assert cfg.db_url_planbar is None
    assert cfg.db_url_tito is None
    assert cfg.uploads_dir is None
    assert cfg.config_dir is None
    assert cfg.include_migrations is True


def test_config_env_override(monkeypatch):
    env = {
        "BACKUP_STORAGE_TYPE": "s3",
        "BACKUP_TENANTS": "kunde1,kunde2",
        "BACKUP_LOCAL_DIR": "/tmp/backups",
        "BACKUP_S3_BUCKET": "planbar-backups",
        "BACKUP_S3_ENDPOINT": "https://s3.example.com",
        "BACKUP_S3_REGION": "eu-central-1",
        "BACKUP_S3_ACCESS_KEY_ID": "AKID",
        "BACKUP_S3_SECRET_ACCESS_KEY": "secret",
        "BACKUP_S3_PATH_PREFIX": "planbar/",
        "BACKUP_RETENTION_DAYS": "14",
        "BACKUP_VERIFY_UPLOAD": "false",
        "BACKUP_LOCK_TTL_SECONDS": "600",
        "BACKUP_DB_URL_PLANBAR": "postgresql://planbar:pw@db_planbar:5432",
        "BACKUP_DB_URL_TITO": "postgresql://tito:pw@db_tito:5432",
        "BACKUP_UPLOADS_DIR": "./uploads/pinboard",
        "BACKUP_CONFIG_DIR": "./config",
        "BACKUP_INCLUDE_MIGRATIONS": "false",
    }
    cfg = _make_config(env, monkeypatch)
    assert cfg.storage_type is StorageType.S3
    assert cfg.tenants == ["kunde1", "kunde2"]
    assert cfg.local_dir == Path("/tmp/backups")
    assert cfg.s3_bucket == "planbar-backups"
    assert cfg.s3_endpoint == "https://s3.example.com"
    assert cfg.s3_region == "eu-central-1"
    assert cfg.s3_access_key_id == "AKID"
    assert cfg.s3_secret_access_key == "secret"
    assert cfg.s3_path_prefix == "planbar/"
    assert cfg.retention_days == 14
    assert cfg.verify_upload is False
    assert cfg.lock_ttl_seconds == 600
    assert cfg.db_url_planbar == "postgresql://planbar:pw@db_planbar:5432"
    assert cfg.db_url_tito == "postgresql://tito:pw@db_tito:5432"
    assert cfg.uploads_dir == Path("./uploads/pinboard")
    assert cfg.config_dir == Path("./config")
    assert cfg.include_migrations is False


def test_config_s3_endpoint_optional(monkeypatch):
    # Endpoint bleibt None -> AWS S3
    cfg = _make_config({"BACKUP_STORAGE_TYPE": "s3", "BACKUP_S3_BUCKET": "b"}, monkeypatch)
    assert cfg.s3_endpoint is None


def test_config_invalid_retention(monkeypatch):
    with pytest.raises(ValidationError):
        _make_config({"BACKUP_RETENTION_DAYS": "-1"}, monkeypatch)


def test_config_storage_type_selection(monkeypatch):
    cfg = _make_config({"BACKUP_STORAGE_TYPE": "local"}, monkeypatch)
    assert cfg.storage_type is StorageType.LOCAL
    cfg = _make_config({"BACKUP_STORAGE_TYPE": "s3", "BACKUP_S3_BUCKET": "b"}, monkeypatch)
    assert cfg.storage_type is StorageType.S3


def test_config_s3_without_bucket_fails(monkeypatch):
    with pytest.raises(ValidationError):
        _make_config({"BACKUP_STORAGE_TYPE": "s3"}, monkeypatch)


def test_config_invalid_storage_type(monkeypatch):
    with pytest.raises(ValidationError):
        _make_config({"BACKUP_STORAGE_TYPE": "dropbox"}, monkeypatch)


def test_config_tenants_strips_whitespace(monkeypatch):
    cfg = _make_config({"BACKUP_TENANTS": " kunde1 ,  kunde2 "}, monkeypatch)
    assert cfg.tenants == ["kunde1", "kunde2"]


def test_exceptions_hierarchy():
    assert issubclass(BackupLockError, BackupError)
    assert issubclass(BackupNotFoundError, BackupError)


def test_exceptions_can_be_raised():
    with pytest.raises(BackupError):
        raise BackupError("boom")
    with pytest.raises(BackupLockError):
        raise BackupLockError("locked")
    with pytest.raises(BackupNotFoundError):
        raise BackupNotFoundError("missing")
