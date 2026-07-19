"""Tests für Schema-Evolution im Restore-Prozess (``app.backup.orchestrator``)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.backup.config import BackupConfig, StorageType
from app.backup.metadata import CURRENT_MANIFEST_VERSION, ComponentEntry, Manifest, Manifest_from_dict
from app.backup.orchestrator import Orchestrator
from app.backup.storage import LocalStorage


def _make_config(tmp_path, **overrides):
    base = dict(
        storage_type=StorageType.LOCAL,
        local_dir=tmp_path / "backups",
        include_migrations=True,
        db_url_planbar=None,
        db_url_tito=None,
        uploads_dir=None,
        config_dir=None,
    )
    base.update(overrides)
    return BackupConfig(**base)


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(root=tmp_path / "backups")


@pytest.fixture
def cfg(tmp_path):
    return _make_config(tmp_path)


def _manifest_with_db(alembic_version: str, key_suffix: str = "planbar_db.dump") -> Manifest:
    return Manifest(
        manifest_version=CURRENT_MANIFEST_VERSION,
        created_at=datetime(2026, 1, 1, 3, 0, 0, tzinfo=timezone.utc),
        tool_version="0.1.0",
        tenant="k1",
        components={
            "planbar_db": ComponentEntry(
                type="postgres_dump",
                format="custom",
                key=f"k1/x/{key_suffix}",
                size_bytes=10,
                checksum_sha256="abc",
                alembic_version=alembic_version,
                migration_history=[alembic_version],
            )
        },
    )


def _seed_dump(storage, dump_bytes=b"DUMP", key="k1/x/planbar_db.dump"):
    storage.upload(key, dump_bytes, metadata={"checksum_sha256": "abc"})


def test_backup_includes_migration_files(cfg, storage):
    uploads_dir = Path(__file__).resolve().parent.parent.parent / "migrations" / "versions"
    orch = Orchestrator(cfg, storage, migrations_dir=uploads_dir)
    manifest = orch.backup_all(tenant="k1")
    assert "migrations" in manifest.components
    assert storage.exists(manifest.components["migrations"].key)


def test_restore_detects_schema_mismatch(cfg, storage, tmp_path, monkeypatch):
    cfg.db_url_planbar = f"sqlite:///{tmp_path}/planbar.db"
    _seed_dump(storage)
    manifest = _manifest_with_db("0001")
    runner = MagicMock()
    monkeypatch.setattr("app.backup.orchestrator.restore_database", MagicMock())
    orch = Orchestrator(cfg, storage, current_schema_version="0012", alembic_runner=runner)
    orch.restore_all(manifest=manifest)
    assert runner.called, "alembic_runner sollte bei Versionsdifferenz aufgerufen werden"


def test_restore_migrates_if_needed(cfg, storage, tmp_path):
    cfg.db_url_planbar = f"sqlite:///{tmp_path}/planbar.db"
    # Realer SQLite-Fallback-Dump, damit Restore klappt
    src = tmp_path / "src.db"
    conn = sqlite3.connect(src)
    conn.executescript(
        "CREATE TABLE foo (id INTEGER PRIMARY KEY, v TEXT);"
        "INSERT INTO foo VALUES (1, 'x');"
        "CREATE TABLE alembic_version (version_num VARCHAR(32));"
        "INSERT INTO alembic_version VALUES ('0001');"
    )
    conn.commit()
    conn.close()
    from app.backup.database import DatabaseBackup

    dump = DatabaseBackup(db_url=f"sqlite:///{src}").dump_sqlalchemy()
    storage.upload("k1/x/planbar_db.dump", dump, metadata={"checksum_sha256": "abc"})
    manifest = _manifest_with_db("0001")

    runner = MagicMock()
    orch = Orchestrator(cfg, storage, current_schema_version="0012", alembic_runner=runner)
    orch.restore_all(manifest=manifest)
    assert runner.call_count == 1


def test_restore_skips_migration_if_matching(cfg, storage, tmp_path, monkeypatch):
    cfg.db_url_planbar = f"sqlite:///{tmp_path}/planbar.db"
    _seed_dump(storage)
    manifest = _manifest_with_db("0012")
    runner = MagicMock()
    monkeypatch.setattr("app.backup.orchestrator.restore_database", MagicMock())
    orch = Orchestrator(cfg, storage, current_schema_version="0012", alembic_runner=runner)
    orch.restore_all(manifest=manifest)
    assert not runner.called, "Bei gleicher Version sollte alembic_runner NICHT laufen"


def test_restore_old_schema_with_new_code(cfg, storage, tmp_path):
    cfg.db_url_planbar = f"sqlite:///{tmp_path}/planbar.db"
    # Legacy-Dump von 0001, aktueller Code kennt 0010 (3 Migrationen weiter)
    src = tmp_path / "src.db"
    conn = sqlite3.connect(src)
    conn.executescript(
        "CREATE TABLE x (id INTEGER PRIMARY KEY); CREATE TABLE alembic_version (version_num VARCHAR(32)); INSERT INTO alembic_version VALUES ('0001');"
    )
    conn.commit()
    conn.close()
    from app.backup.database import DatabaseBackup

    dump = DatabaseBackup(db_url=f"sqlite:///{src}").dump_sqlalchemy()
    storage.upload("k1/x/planbar_db.dump", dump, metadata={"checksum_sha256": "abc"})
    manifest = _manifest_with_db("0001")
    runner = MagicMock()
    orch = Orchestrator(cfg, storage, current_schema_version="0010", alembic_runner=runner)
    orch.restore_all(manifest=manifest)
    assert runner.called


def test_manifest_version_migration():
    # Manifest ohne manifest_version -> v0.9-Format -> wird zur aktuellen Version migriert
    legacy = {
        "created_at": "2026-01-01T03:00:00Z",
        "tool_version": "0.0.9",
        "tenant": "k1",
        "db": {"key": "k1/20260101-030000/planbar_db.dump", "size_bytes": 100, "checksum_sha256": "x"},
    }
    manifest = Manifest_from_dict(legacy)
    assert manifest.manifest_version == CURRENT_MANIFEST_VERSION
    assert "planbar_db" in manifest.components
