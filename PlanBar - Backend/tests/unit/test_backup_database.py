"""Tests für ``app.backup.database``.

Diese Tests decken beide Pfade ab:
* pg_dump/pg_restore via subprocess (gemockt) – produktiver Pfad
* SQLAlchemy-basierter Fallback – für SQLite/Dev & Tests
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine

from app.backup.database import (
    DatabaseBackup,
    discover_tenants,
    dump_database,
    restore_database,
)


# ---------------------------------------------------------------------------
# Alembic-Version
# ---------------------------------------------------------------------------


def test_get_alembic_current_version(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);"
        "INSERT INTO alembic_version (version_num) VALUES ('0010');"
    )
    conn.commit()
    conn.close()

    db = DatabaseBackup(db_url=f"sqlite:///{db_path}")
    version = db.get_alembic_current_version()
    assert version == "0010"


def test_get_alembic_current_version_empty(tmp_path):
    db_path = tmp_path / "empty.db"
    db = DatabaseBackup(db_url=f"sqlite:///{db_path}")
    assert db.get_alembic_current_version() is None


def test_get_alembic_migration_history(tmp_path):
    migrations = tmp_path / "versions"
    migrations.mkdir()
    (migrations / "0001_initial.py").write_text(
        '"""initial\n\nRevision ID: 0001\n"""\nrevision = "0001"\ndown_revision = None\n'
    )
    (migrations / "0002_next.py").write_text('revision = "0002"\ndown_revision = "0001"\n')
    (migrations / "0010_more.py").write_text('revision = "0010"\ndown_revision = "0002"\n')
    db = DatabaseBackup(db_url=f"sqlite:///{tmp_path}/x.db")
    history = db.get_alembic_migration_history(migrations_dir=migrations)
    assert history == ["0001", "0002", "0010"]


# ---------------------------------------------------------------------------
# SQLAlchemy-Fallback Dump
# ---------------------------------------------------------------------------


def _create_simple_db(path: Path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        INSERT INTO users (id, name) VALUES (1, 'Alice');
        INSERT INTO users (id, name) VALUES (2, 'Bob');
        CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);
        INSERT INTO alembic_version (version_num) VALUES ('0001');
        """
    )
    conn.commit()
    conn.close()


def test_dump_database_via_sqlalchemy(tmp_path):
    src = tmp_path / "src.db"
    _create_simple_db(src)

    db = DatabaseBackup(db_url=f"sqlite:///{src}")
    dump_bytes = db.dump_sqlalchemy()
    data = json.loads(dump_bytes)

    assert data["alembic_version"] == "0001"
    assert "users" in data["tables"]
    rows = data["tables"]["users"]["rows"]
    assert {r["name"] for r in rows} == {"Alice", "Bob"}


def test_restore_database_sqlalchemy_fallback(tmp_path):
    src = tmp_path / "src.db"
    _create_simple_db(src)
    db = DatabaseBackup(db_url=f"sqlite:///{src}")
    dump_bytes = db.dump_sqlalchemy()

    target = tmp_path / "target.db"
    target_db = DatabaseBackup(db_url=f"sqlite:///{target}")
    target_db.restore_sqlalchemy(dump_bytes)

    # Verify round-trip
    conn = sqlite3.connect(target)
    rows = conn.execute("SELECT name FROM users ORDER BY id").fetchall()
    conn.close()
    assert [r[0] for r in rows] == ["Alice", "Bob"]


# ---------------------------------------------------------------------------
# pg_dump via Subprocess (gemockt)
# ---------------------------------------------------------------------------


def test_dump_database_via_pg_dump(tmp_path):
    db = DatabaseBackup(db_url="postgresql://planbar:pw@db_planbar:5432/kunde1")
    expected = b"PGDMP-CONTENT"
    with patch("app.backup.database.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=expected, returncode=0)
        result = db.dump_pg_dump()
    assert result == expected
    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert "pg_dump" in cmd
    assert "--format=custom" in cmd
    assert any("kunde1" in c for c in cmd)


def test_dump_database_failure(tmp_path):
    db = DatabaseBackup(db_url="postgresql://planbar:pw@db_planbar:5432/kunde1")
    with patch("app.backup.database.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=b"", returncode=1, stderr=b"connection refused")
        with pytest.raises(RuntimeError):
            db.dump_pg_dump()


def test_restore_database_from_bytes(tmp_path):
    db = DatabaseBackup(db_url="postgresql://planbar:pw@db_planbar:5432/kunde1")
    with patch("app.backup.database.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        db.restore_pg_restore(b"PGDMP")
    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert "pg_restore" in cmd
    assert "--clean" in cmd


# ---------------------------------------------------------------------------
# Dispatch dump_database / restore_database
# ---------------------------------------------------------------------------


def test_dump_database_dispatch_sqlite(tmp_path):
    src = tmp_path / "src.db"
    _create_simple_db(src)
    db = DatabaseBackup(db_url=f"sqlite:///{src}")
    data = dump_database(db)
    assert json.loads(data)["alembic_version"] == "0001"


def test_dump_database_dispatch_postgres(tmp_path):
    db = DatabaseBackup(db_url="postgresql://u:p@host:5432/db")
    with patch("app.backup.database.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=b"PGDMP", returncode=0)
        result = dump_database(db)
    assert result == b"PGDMP"


def test_restore_database_dispatch_sqlite(tmp_path):
    src = tmp_path / "src.db"
    _create_simple_db(src)
    db = DatabaseBackup(db_url=f"sqlite:///{src}")
    dump_bytes = db.dump_sqlalchemy()
    target = tmp_path / "target.db"
    db_target = DatabaseBackup(db_url=f"sqlite:///{target}")
    restore_database(db_target, dump_bytes)

    conn = sqlite3.connect(target)
    rows = conn.execute("SELECT name FROM users ORDER BY id").fetchall()
    conn.close()
    assert [r[0] for r in rows] == ["Alice", "Bob"]


def test_restore_database_dispatch_postgres(tmp_path):
    db = DatabaseBackup(db_url="postgresql://u:p@host:5432/db")
    with patch("app.backup.database.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        restore_database(db, b"PGDMP-CONTENT")
    assert mock_run.called


# ---------------------------------------------------------------------------
# Tenant-Discovery
# ---------------------------------------------------------------------------


def test_discover_tenants_from_db():
    # Simuliert das Ergebnis der SQL-Query ``SELECT datname FROM pg_database WHERE
    # datname LIKE '%_planbar'`` – Filterung übernimmt das DB-System.
    fake_rows = [("kunde1_planbar",), ("kunde2_planbar",)]
    mock_result = MagicMock()
    mock_result.fetchall.return_value = fake_rows
    mock_result.__iter__ = lambda self_: iter(fake_rows)
    mock_result.__next__ = lambda self_: next(iter(fake_rows))
    mock_conn = MagicMock()
    mock_conn.execute.return_value = mock_result
    mock_engine = MagicMock()
    mock_engine.dialect.name = "postgresql"
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    with patch("app.backup.database.create_engine", return_value=mock_engine):
        tenants = discover_tenants("postgresql://u:p@h/db")
    assert "kunde1_planbar" in tenants
    assert "kunde2_planbar" in tenants


def test_discover_tenants_from_config():
    with patch("app.backup.database.create_engine", side_effect=Exception("no db")):
        tenants = discover_tenants("postgresql://invalid", fallback=["k1", "k2"])
    assert tenants == ["k1", "k2"]


def test_discover_tenants_empty_fallback():
    with patch("app.backup.database.create_engine", side_effect=Exception("no db")):
        tenants = discover_tenants("postgresql://invalid")
    assert tenants == []


def test_discover_tenants_sqlite_returns_empty():
    # SQLite kennt keine pg_database; die Funktion greift sauber auf Fallback zurueck.
    engine = create_engine("sqlite:///:memory:")
    with patch("app.backup.database.create_engine", return_value=engine):
        tenants = discover_tenants("sqlite:///:memory:", fallback=["explicit"])
    assert tenants == ["explicit"]


# ---------------------------------------------------------------------------
# Migration-Archiv
# ---------------------------------------------------------------------------


def test_backup_schema_migrations(tmp_path):
    migrations = tmp_path / "versions"
    migrations.mkdir()
    (migrations / "0001_initial.py").write_text('revision = "0001"\ndown_revision = None\n')
    (migrations / "0002_next.py").write_text('revision = "0002"\ndown_revision = "0001"\n')

    db = DatabaseBackup(db_url=f"sqlite:///{tmp_path}/x.db")
    archive_bytes = db.archive_migrations_dir(migrations)
    assert isinstance(archive_bytes, bytes)
    assert len(archive_bytes) > 0


def test_restore_with_old_schema(tmp_path):
    # Alte Version 0001 im Dump, neue Version 0010 ist im Codebase-Code.
    src = tmp_path / "src.db"
    _create_simple_db(src)
    db = DatabaseBackup(db_url=f"sqlite:///{src}")
    dump_bytes = db.dump_sqlalchemy()
    data = json.loads(dump_bytes)
    assert data["alembic_version"] == "0001"  # "alt"

    # Restore -> Schema ist zwar alt, aber Datei kann geladen werden.
    target = tmp_path / "target.db"
    target_db = DatabaseBackup(db_url=f"sqlite:///{target}")
    target_db.restore_sqlalchemy(dump_bytes)
    assert target.exists()
