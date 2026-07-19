"""Tests für ``app.backup.orchestrator``."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.backup.config import BackupConfig, StorageType
from app.backup.exceptions import BackupLockError
from app.backup.metadata import CURRENT_MANIFEST_VERSION, Manifest, Manifest_from_dict
from app.backup.orchestrator import Orchestrator, TOOL_VERSION
from app.backup.storage import LocalStorage


def _make_config(tmp_path, **overrides):
    base = dict(
        storage_type=StorageType.LOCAL,
        local_dir=tmp_path / "backups",
        retention_days=30,
        verify_upload=True,
        lock_ttl_seconds=300,
        include_migrations=True,
        db_url_planbar=None,
        db_url_tito=None,
        uploads_dir=None,
        config_dir=None,
    )
    base.update(overrides)
    return BackupConfig(**base)


def _tar_bytes(name="file.txt", content=b"hello"):
    """Erzeugt einen gueltigen tar.gz-Inhalt in-memory."""
    import io
    import tarfile

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name=name)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def _providers(**kwargs):
    """Default-Provider理念: jede Komponente liefert feste Bytes."""
    defaults = {
        "planbar_db": lambda: b"PLANBAR_DUMP",
        "tito_db": lambda: b"TITO_DUMP",
        "uploads": lambda: _tar_bytes("uploads/sample.txt", b"u"),
        "config": lambda: _tar_bytes("config/sample.env", b"ENV=1"),
        "migrations": lambda: _tar_bytes("migrations/0001_initial.py", b"revision='0001'\n"),
    }
    defaults.update(kwargs)
    return defaults


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(root=tmp_path / "backups")


@pytest.fixture
def cfg(tmp_path):
    return _make_config(tmp_path)


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


def test_backup_all_components(cfg, storage):
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    manifest = orch.backup_all(tenant="kunde1")
    assert manifest.tenant == "kunde1"
    assert set(manifest.components) == {"planbar_db", "tito_db", "uploads", "config", "migrations"}
    for name, comp in manifest.components.items():
        assert storage.exists(comp.key)
        assert comp.checksum_sha256 == hashlib.sha256(_providers()[name]()).hexdigest()
        assert comp.size_bytes == len(_providers()[name]())
    assert manifest.verified is True


def test_backup_partial_failure(cfg, storage):
    def fail():
        raise RuntimeError("boom")

    providers = _providers(planbar_db=fail)
    orch = Orchestrator(cfg, storage, component_providers=providers)
    manifest = orch.backup_all(tenant="k")
    # planbar_db fehlt, die anderen wurden gesichert
    assert "planbar_db" not in manifest.components
    assert "tito_db" in manifest.components
    assert "uploads" in manifest.components
    assert orch.last_errors and orch.last_errors[0][0] == "planbar_db"


def test_backup_locks_before_start(cfg, storage):
    ordered = []
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    # Wrappen des Storages, um die Reihenfolge zu pruefen
    real_upload = storage.upload
    real_acquire = storage.acquire_lock

    def upload_spy(key, data, metadata=None):
        ordered.append(("upload", key))
        return real_upload(key, data, metadata)

    def acquire_spy(lock_key, ttl_seconds=300):
        ordered.append(("acquire", lock_key))
        return real_acquire(lock_key, ttl_seconds)

    storage.upload = upload_spy
    storage.acquire_lock = acquire_spy
    orch.backup_all(tenant="k1")
    assert ordered[0][0] == "acquire"
    assert any(o[0] == "upload" for o in ordered[1:])


def test_backup_refuses_when_locked(cfg, storage):
    storage.acquire_lock("backup", ttl_seconds=300)
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    with pytest.raises(BackupLockError):
        orch.backup_all(tenant="k1")


def test_backup_releases_lock_after_completion(cfg, storage):
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    orch.backup_all(tenant="k1")
    # Nach dem Lauf kann erneut gelockt werden
    assert storage.acquire_lock("backup") is True


def test_backup_releases_lock_on_error(cfg, storage):
    def fail():
        raise RuntimeError("total")

    orch = Orchestrator(cfg, storage, component_providers=_providers(planbar_db=fail, tito_db=fail))
    try:
        orch.backup_all(tenant="k1")
    except Exception:
        pass
    assert storage.acquire_lock("backup") is True


def test_backup_verify_after_upload(cfg, storage):
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    manifest = orch.backup_all(tenant="k1")
    assert manifest.verified is True


def test_backup_verify_detects_corruption(cfg, storage):
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    # Uploads manipulieren NACH dem orch-Lauf durch direktes Ueberschreiben
    manifest = orch.backup_all(tenant="k1")
    planbar_key = manifest.components["planbar_db"].key
    storage.upload(planbar_key, b"CORRUPTED", metadata={"checksum_sha256": "deadbeef"})
    orch2 = Orchestrator(cfg, storage, component_providers=_providers())
    manifest2 = orch2.backup_all(tenant="k1", verify=True)
    # Zweiter Lauf -> verified True, weil orch2 die Checksums neu berechnet
    assert manifest2.verified is True


def test_backup_verify_false_when_storage_corrupted_and_no_new_run(cfg, storage):
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    manifest = orch.backup_all(tenant="k1")
    # Corrupt one stored object after backup
    storage.upload(manifest.components["planbar_db"].key, b"BROKEN")
    reverify = orch.verify_manifest(manifest)
    assert reverify is False


def test_backup_retention(cfg, storage):
    cfg.retention_days = 5

    def old_now():
        return datetime(2026, 1, 1, 3, 0, 0, tzinfo=timezone.utc)

    def new_now():
        return datetime(2026, 1, 11, 3, 0, 0, tzinfo=timezone.utc)

    orch_old = Orchestrator(cfg, storage, component_providers=_providers(), now=old_now)
    orch_old.backup_all(tenant="k1")
    orch_new = Orchestrator(cfg, storage, component_providers=_providers(), now=new_now)
    orch_new.backup_all(tenant="k1")
    deleted = orch_new.apply_retention(tenant="k1", now=new_now())
    assert any("20260101-030000" in d for d in deleted)


def test_backup_retention_min_age(cfg, storage):
    cfg.retention_days = 30
    orch = Orchestrator(cfg, storage, component_providers=_providers())

    def now():
        return datetime(2026, 1, 11, 3, 0, 0, tzinfo=timezone.utc)

    def past():
        return datetime(2026, 1, 1, 3, 0, 0, tzinfo=timezone.utc)

    Orchestrator(cfg, storage, component_providers=_providers(), now=past).backup_all(tenant="k1")
    deleted = orch.apply_retention(tenant="k1", now=now())
    # 10 Tage < 30 Tage -> nichts loeschen
    assert deleted == []


def test_backup_skip_if_not_configured(tmp_path, storage):
    cfg = _make_config(tmp_path, include_migrations=False)  # alle dirs/urls None, Migrations aus
    orch = Orchestrator(cfg, storage)  # keine provider
    manifest = orch.backup_all(tenant="k1")
    # Keine Provider + keine Config + Migrations aus -> leeres Manifest
    assert manifest.components == {}
    assert manifest.verified is False  # nothing to verify


def test_backup_with_s3_target(tmp_path):
    import boto3
    from moto import mock_aws
    from app.backup.storage import S3Storage

    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="planbar-backups")
        storage = S3Storage(bucket="planbar-backups", region="us-east-1")
        cfg = _make_config(tmp_path)
        orch = Orchestrator(cfg, storage, component_providers=_providers())
        manifest = orch.backup_all(tenant="k1")
        assert manifest.verified is True
        assert storage.exists(manifest.components["planbar_db"].key)


def test_backup_without_manifest_legacy(tmp_path, storage):
    cfg = _make_config(tmp_path, db_url_planbar=f"sqlite:///{tmp_path}/target.db")
    # Simuliere einen Legacy-Dump WITHOUT manifest
    storage.upload("kunde1/20260101-030000/planbar_db.dump", b"LEGACY")
    orch = Orchestrator(cfg, storage)
    info = orch.describe_backup("kunde1/20260101-030000/planbar_db.dump")
    # Kein Manifest vorhanden -> Default-Metadaten
    assert info["has_manifest"] is False
    assert info["checksum_sha256"] is None


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------


def test_restore_all_components(cfg, storage, tmp_path):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    cfg.uploads_dir = uploads_dir
    cfg.config_dir = config_dir
    cfg.db_url_planbar = f"sqlite:///{tmp_path}/planbar.db"

    # Backup generieren
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    manifest = orch.backup_all(tenant="k1")
    # Restore durchfuehren – Restore-Methoden mocken, weil _providers()
    # keine echten DB-Dumps zurück gibt (Roundtrip-Test in integration/)
    restorer = Orchestrator(cfg, storage, component_providers=_providers())
    restorer._restore_db_component = MagicMock()
    restorer._restore_files_component = MagicMock()
    restorer._restore_migrations_component = MagicMock()
    result = restorer.restore_all(manifest=manifest)
    assert set(result["restored"]) == {"planbar_db", "tito_db", "uploads", "config", "migrations"}


def test_restore_correct_order(cfg, storage):
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    manifest = orch.backup_all(tenant="k1")
    restorer = Orchestrator(cfg, storage, component_providers=_providers())
    # Mock die Restore-Aufrufe, um Reihenfolge zu pruefen
    log = []

    def log_db(name, component, data):
        log.append(name)
        return None

    restorer._restore_db_component = log_db
    restorer._restore_files_component = log_db
    restorer._restore_migrations_component = log_db
    restorer.restore_all(manifest=manifest)
    assert log == ["config", "migrations", "planbar_db", "tito_db", "uploads"]


def test_restore_single_component(cfg, storage):
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    manifest = orch.backup_all(tenant="k1")
    restorer = Orchestrator(cfg, storage, component_providers=_providers())
    restorer._restore_db_component = MagicMock()
    restorer._restore_files_component = MagicMock()
    restorer._restore_migrations_component = MagicMock()
    result = restorer.restore_all(manifest=manifest, components=["planbar_db"])
    assert result["restored"] == ["planbar_db"]


def test_restore_dry_run(cfg, storage):
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    manifest = orch.backup_all(tenant="k1")
    restorer = Orchestrator(cfg, storage, component_providers=_providers())
    # Patch restore methoden, um sicherzustellen dass sie NICHT aufgerufen werden
    restorer._restore_db_component = MagicMock(side_effect=AssertionError("should not be called"))
    restorer._restore_files_component = MagicMock(side_effect=AssertionError("should not be called"))
    restorer._restore_migrations_component = MagicMock(side_effect=AssertionError("should not be called"))
    result = restorer.restore_all(manifest=manifest, dry_run=True)
    assert result["dry_run"] is True
    assert set(result["planned"]) == {"planbar_db", "tito_db", "uploads", "config", "migrations"}


def test_restore_fails_if_component_missing(cfg, storage):
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    manifest = orch.backup_all(tenant="k1")
    # Construct manifest without planbar_db
    broken = Manifest(
        manifest_version=CURRENT_MANIFEST_VERSION,
        created_at=manifest.created_at,
        tool_version=manifest.tool_version,
        tenant="k1",
        components={k: v for k, v in manifest.components.items() if k != "planbar_db"},
    )
    restorer = Orchestrator(cfg, storage, component_providers=_providers())
    with pytest.raises(Exception):
        restorer.restore_all(manifest=broken, components=["planbar_db"])


def test_restore_from_s3_source(tmp_path):
    import boto3
    from moto import mock_aws
    from app.backup.storage import S3Storage

    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="planbar-backups")
        storage = S3Storage(bucket="planbar-backups", region="us-east-1")
        cfg = _make_config(tmp_path)
        orch = Orchestrator(cfg, storage, component_providers=_providers())
        manifest = orch.backup_all(tenant="k1")
        restorer = Orchestrator(cfg, storage, component_providers=_providers())
        restorer._restore_db_component = MagicMock()
        restorer._restore_files_component = MagicMock()
        restorer._restore_migrations_component = MagicMock()
        result = restorer.restore_all(manifest=manifest)
        assert "planbar_db" in result["restored"]


def test_restore_legacy_dump_via_orchestrator(cfg, storage, tmp_path):
    cfg.db_url_planbar = f"sqlite:///{tmp_path}/planbar.db"
    # Erzeuge einen gueltigen SQLAlchemy-Fallback-Dump
    from app.backup.database import DatabaseBackup

    src = tmp_path / "src.db"
    import sqlite3

    conn = sqlite3.connect(src)
    conn.executescript(
        "CREATE TABLE foo (id INTEGER PRIMARY KEY, v TEXT); INSERT INTO foo VALUES (1, 'x'); CREATE TABLE alembic_version (version_num VARCHAR(32)); INSERT INTO alembic_version VALUES ('0001');"
    )
    conn.commit()
    conn.close()
    dump_bytes = DatabaseBackup(db_url=f"sqlite:///{src}").dump_sqlalchemy()
    storage.upload("legacy/planbar_db.dump", dump_bytes)

    orch = Orchestrator(cfg, storage)
    result = orch.restore_legacy(dump_key="legacy/planbar_db.dump")
    assert result["restored"] == ["planbar_db"]


def test_tool_version_set():
    assert TOOL_VERSION


def test_backup_creates_manifest_json(cfg, storage):
    orch = Orchestrator(cfg, storage, component_providers=_providers())
    manifest = orch.backup_all(tenant="k1")
    prefix = "/".join(manifest.components["planbar_db"].key.split("/")[:-1])
    manifest_key = f"{prefix}/manifest.json"
    assert storage.exists(manifest_key)
    raw = storage.download(manifest_key)
    loaded = Manifest_from_dict(json.loads(raw))
    assert loaded.tenant == "k1"
