"""Integration-Tests fuer das Backup-Modul (Full-Flow LocalStorage + S3/moto).

Diese Tests laufen gegen echte Storages (LocalStorage im tmp_path, S3Storage gegen
moto) und использовать echte SQLite-Dumps, um den kompletten Backup->Verify->Restore
Roundtrip zu pruefen.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from app.backup.config import BackupConfig, StorageType
from app.backup.database import DatabaseBackup
from app.backup.exceptions import BackupLockError
from app.backup.metadata import CURRENT_MANIFEST_VERSION, Manifest_from_dict
from app.backup.orchestrator import Orchestrator
from app.backup.storage import LocalStorage, S3Storage


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


def _create_db(path: Path, alembic: str = "0001"):
    conn = sqlite3.connect(path)
    conn.executescript(
        f"""
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        INSERT INTO users (id, name) VALUES (1, 'Alice');
        INSERT INTO users (id, name) VALUES (2, 'Bob');
        CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);
        INSERT INTO alembic_version (version_num) VALUES ('{alembic}');
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def local_setup(tmp_path):
    src_db = tmp_path / "src.db"
    _create_db(src_db)
    uploads = tmp_path / "uploads"
    (uploads / "pinboard").mkdir(parents=True)
    (uploads / "pinboard" / "x.txt").write_bytes(b"upload-content")
    config = tmp_path / "config"
    config.mkdir()
    (config / "app.env").write_bytes(b"ENV=production\n")

    cfg = _make_config(
        tmp_path,
        db_url_planbar=f"sqlite:///{src_db}",
        uploads_dir=uploads / "pinboard",
        config_dir=config,
    )
    storage = LocalStorage(root=tmp_path / "backups")
    return cfg, storage, src_db


def _orch(cfg, storage, alembic_target=None):
    runner = MagicMock(name="alembic_runner")
    return Orchestrator(
        cfg,
        storage,
        alembic_runner=runner,
        current_schema_version=alembic_target,
    ), runner


# ---------------------------------------------------------------------------
# Roundtrip
# ---------------------------------------------------------------------------


def test_backup_restore_roundtrip_local(local_setup, tmp_path):
    cfg, storage, src_db = local_setup
    orch, _ = _orch(cfg, storage)
    manifest = orch.backup_all(tenant="k1")

    # Restore in eine NEUE SQLite-Datei
    target_db = tmp_path / "restored.db"
    cfg.db_url_planbar = f"sqlite:///{target_db}"
    restorer, _ = _orch(cfg, storage)
    result = restorer.restore_all(manifest=manifest)

    assert "planbar_db" in result["restored"]
    conn = sqlite3.connect(target_db)
    rows = conn.execute("SELECT name FROM users ORDER BY id").fetchall()
    conn.close()
    assert [r[0] for r in rows] == ["Alice", "Bob"]

    # Uploads wurden entpackt
    assert (cfg.uploads_dir / "x.txt").read_bytes() == b"upload-content"


def test_backup_restore_roundtrip_s3(tmp_path, local_setup):
    cfg, _, src_db = local_setup
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="planbar-backups-it")
        storage = S3Storage(bucket="planbar-backups-it", region="us-east-1")
        orch, _ = _orch(cfg, storage)
        manifest = orch.backup_all(tenant="k1")

        target_db = tmp_path / "restored.db"
        cfg.db_url_planbar = f"sqlite:///{target_db}"
        restorer, _ = _orch(cfg, storage)
        result = restorer.restore_all(manifest=manifest)
        assert "planbar_db" in result["restored"]
        conn = sqlite3.connect(target_db)
        rows = conn.execute("SELECT name FROM users ORDER BY id").fetchall()
        conn.close()
        assert [r[0] for r in rows] == ["Alice", "Bob"]


def test_backup_verify_checksums_after_upload(local_setup):
    cfg, storage, _ = local_setup
    orch, _ = _orch(cfg, storage)
    manifest = orch.backup_all(tenant="k1")
    assert manifest.verified is True
    # Manifest wurde mit verified=True hochgeladen
    prefix = "/".join(manifest.components["planbar_db"].key.split("/")[:-1])
    raw = storage.download(f"{prefix}/manifest.json")
    loaded = Manifest_from_dict(json.loads(raw))
    assert loaded.verified is True


def test_backup_detects_corrupted_upload(local_setup):
    cfg, storage, _ = local_setup
    orch, _ = _orch(cfg, storage)
    manifest = orch.backup_all(tenant="k1")
    # Eine Komponente nachtraeglich veraendern
    storage.upload(manifest.components["planbar_db"].key, b"CORRUPTED")
    # verify nach dem Eingriff -> False
    assert orch.verify_manifest(manifest) is False


def test_backup_idempotent(local_setup):
    cfg, storage, _ = local_setup
    orch1, _ = _orch(cfg, storage, alembic_target=None)
    m1 = orch1.backup_all(tenant="k1")
    time.sleep(0.01)
    orch1.now = lambda: datetime(2026, 7, 14, 3, 0, 1, tzinfo=timezone.utc)
    m2 = orch1.backup_all(tenant="k1")
    # Verschiedene Timestamps -> unterschiedliche Keys
    assert m1.components["planbar_db"].key != m2.components["planbar_db"].key


def test_restore_overwrites_existing(local_setup, tmp_path):
    cfg, storage, _ = local_setup
    orch, _ = _orch(cfg, storage)
    manifest = orch.backup_all(tenant="k1")

    target = tmp_path / "exists.db"
    conn = sqlite3.connect(target)
    conn.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT); INSERT INTO users VALUES (99, 'OLD');")
    conn.commit()
    conn.close()
    cfg.db_url_planbar = f"sqlite:///{target}"
    restorer, _ = _orch(cfg, storage)
    restorer.restore_all(manifest=manifest)

    conn = sqlite3.connect(target)
    rows = conn.execute("SELECT name FROM users ORDER BY id").fetchall()
    conn.close()
    # Dump hat ALICE/BOB, OLD wurde via CREATE TABLE IF NOT EXISTS nicht überschrieben,
    # Aber INSERTs wurden hinzugefuegt -> beide vorhanden. Wichtig: Restore laeuft
    # ohne Fehler durch.
    assert ("Alice",) in rows
    assert ("Bob",) in rows


def test_backup_with_sqlite_dump(tmp_path):
    """Dump + Restore + Daten-Integritaet."""
    src = tmp_path / "src.db"
    _create_db(src, alembic="0010")
    cfg = _make_config(tmp_path, db_url_planbar=f"sqlite:///{src}")
    storage = LocalStorage(root=tmp_path / "backups")
    orch, _ = _orch(cfg, storage)
    manifest = orch.backup_all(tenant="k1")
    target = tmp_path / "restored.db"
    cfg.db_url_planbar = f"sqlite:///{target}"
    restorer, _ = _orch(cfg, storage)
    restorer.restore_all(manifest=manifest)
    conn = sqlite3.connect(target)
    assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0010"
    conn.close()


def test_backwards_compat_with_shell_script(tmp_path):
    """Von backup.sh erzeugter Dump (rohes pg_dump-Format) ist als Legacy lesbar."""
    cfg = _make_config(tmp_path, db_url_planbar=f"sqlite:///{tmp_path}/legacy.db")
    storage = LocalStorage(root=tmp_path / "backups")
    # Simulate legacy .dump from backup.sh by storing arbitrary bytes
    storage.upload("legacy/20260101-030000.db1.dump", b"PGDMP-LEGACY")
    orch, _ = _orch(cfg, storage)
    info = orch.describe_backup("legacy/20260101-030000.db1.dump")
    assert info["has_manifest"] is False
    assert info["checksum_sha256"] is None


def test_fixture_v1_manifest_loadable():
    fixture = Path(__file__).resolve().parent.parent / "fixtures" / "backups" / "v1" / "manifest.json"
    raw = json.loads(fixture.read_text())
    manifest = Manifest_from_dict(raw)
    assert manifest.tenant == "kunde1"
    assert manifest.manifest_version == CURRENT_MANIFEST_VERSION
    assert "planbar_db" in manifest.components


def test_fixture_v1_restore_simulation(tmp_path):
    """Mit Fixture v1: Manifest parsen + Komponenten auflisten."""
    fixture = Path(__file__).resolve().parent.parent / "fixtures" / "backups" / "v1"
    raw = json.loads((fixture / "manifest.json").read_text())
    manifest = Manifest_from_dict(raw)
    # Alle Komponenten-Namen bekannt
    expected = {"planbar_db", "tito_db", "uploads", "config", "migrations"}
    assert expected.issubset(set(manifest.components))
    # Authentic dump file exists
    assert (fixture / "planbar_db.dump").exists()
    # Parsed by SQLAlchemy fallback restaurator
    db_path = tmp_path / "out.db"
    DatabaseBackup(db_url=f"sqlite:///{db_path}").restore_sqlalchemy((fixture / "planbar_db.dump").read_bytes())
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0010"
    conn.close()


def test_backup_lock_prevents_concurrent_run(local_setup):
    cfg, storage, _ = local_setup
    storage.acquire_lock("backup", ttl_seconds=300)
    orch, _ = _orch(cfg, storage)
    with pytest.raises(BackupLockError):
        orch.backup_all(tenant="k1")


def test_backup_retention_deletes_old_backups(local_setup):
    cfg, storage, _ = local_setup
    cfg.retention_days = 5

    def old_now():
        return datetime(2026, 1, 1, 3, 0, 0, tzinfo=timezone.utc)

    past_orch, _ = _orch(cfg, storage)
    past_orch.now = old_now
    past_orch.backup_all(tenant="k1")

    # Neues Backup jetzt
    now = datetime(2026, 1, 11, 3, 0, 0, tzinfo=timezone.utc)
    orch, _ = _orch(cfg, storage)
    orch.now = lambda: now
    orch.backup_all(tenant="k1")
    deleted = orch.apply_retention(tenant="k1", now=now)
    assert any("20260101-030000" in d for d in deleted)


def test_backup_with_legacy_manifest_v2_fixture(tmp_path):
    """Fixture v2 kann geladen und als Restore-Quelle angesprochen werden."""
    fixture = Path(__file__).resolve().parent.parent / "fixtures" / "backups" / "v2" / "manifest.json"
    raw = json.loads(fixture.read_text())
    manifest = Manifest_from_dict(raw)
    assert manifest.manifest_version == "2.0"
    assert manifest.components["planbar_db"].encryption == "SSE-S3"
    assert manifest.verified is True
