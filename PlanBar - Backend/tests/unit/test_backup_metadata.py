"""Tests für `app.backup.metadata` (Manifest + Migrationen)."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.backup.exceptions import ManifestError
from app.backup.metadata import (
    MANIFEST_MIGRATORS,
    CURRENT_MANIFEST_VERSION,
    ComponentEntry,
    Manifest,
    Manifest_from_dict,
    _migrate_v09_to_v10,
    _migrate_v10_to_v20,
)


def _make_component(**overrides) -> dict:
    base = {
        "type": "postgres_dump",
        "format": "custom",
        "key": "kunde1/20260714-030000/planbar_db.dump",
        "size_bytes": 1024,
        "checksum_sha256": "abc123",
    }
    base.update(overrides)
    return base


def test_manifest_create_minimal():
    manifest = Manifest(
        manifest_version="1.0",
        created_at=datetime(2026, 7, 14, 3, 0, 0, tzinfo=timezone.utc),
        tool_version="0.1.0",
        tenant="kunde1",
        verified=False,
        components={"planbar_db": ComponentEntry(**_make_component())},
    )
    assert manifest.manifest_version == "1.0"
    assert manifest.tenant == "kunde1"
    assert manifest.verified is False
    assert set(manifest.components) == {"planbar_db"}


def test_manifest_create_full():
    components = {
        "planbar_db": ComponentEntry(
            type="postgres_dump",
            format="custom",
            alembic_version="0010",
            migration_history=["0001", "0010"],
            key="kunde1/x/planbar_db.dump",
            size_bytes=100,
            checksum_sha256="a",
        ),
        "tito_db": ComponentEntry(
            type="postgres_dump",
            format="custom",
            schema_version="1.0",
            key="kunde1/x/tito_db.dump",
            size_bytes=50,
            checksum_sha256="b",
        ),
        "uploads": ComponentEntry(type="tar_gz", key="kunde1/x/uploads.tar.gz", size_bytes=1024, checksum_sha256="c"),
        "config": ComponentEntry(type="env_dir", key="kunde1/x/config.tar.gz", size_bytes=10, checksum_sha256="d"),
        "migrations": ComponentEntry(
            type="directory_archive", key="kunde1/x/migrations.tar.gz", size_bytes=20, checksum_sha256="e"
        ),
    }
    manifest = Manifest(
        manifest_version="1.0",
        created_at=datetime(2026, 7, 14, 3, 0, 0, tzinfo=timezone.utc),
        tool_version="0.1.0",
        tenant="kunde1",
        verified=False,
        components=components,
    )
    assert len(manifest.components) == 5
    assert manifest.components["planbar_db"].alembic_version == "0010"
    assert manifest.components["tito_db"].schema_version == "1.0"


def test_manifest_serialize_deserialize():
    manifest = Manifest(
        manifest_version="1.0",
        created_at=datetime(2026, 7, 14, 3, 0, 0, tzinfo=timezone.utc),
        tool_version="0.1.0",
        tenant="kunde1",
        verified=False,
        components={"planbar_db": ComponentEntry(**_make_component())},
    )
    data = manifest.to_dict()
    s = json.dumps(data)
    restored = Manifest_from_dict(json.loads(s))
    # 1.0 wird beim Laden zur aktuellen Version migriert
    assert restored.manifest_version == CURRENT_MANIFEST_VERSION
    assert restored.tenant == "kunde1"
    assert restored.components["planbar_db"].key == "kunde1/20260714-030000/planbar_db.dump"
    assert restored.components["planbar_db"].size_bytes == 1024


def test_manifest_validation():
    with pytest.raises(Exception):
        Manifest(
            manifest_version="1.0",
            created_at="not-a-date",
            tool_version="0.1.0",
            tenant="x",
            verified=False,
            components={},
        )


def test_manifest_version_check_unknown_version():
    with pytest.raises(ManifestError):
        Manifest_from_dict({"manifest_version": "9.9", "components": {}, "tenant": "x"})


def test_manifest_v1_fixture_loadable():
    fixture = Path(__file__).resolve().parent.parent / "fixtures" / "backups" / "v1" / "manifest.json"
    raw = json.loads(fixture.read_text())
    manifest = Manifest_from_dict(raw)
    assert manifest.tenant == "kunde1"
    assert "planbar_db" in manifest.components


def test_manifest_backward_compat_v1():
    # v1 Fixture laed sich via Migration in die aktuelle Version
    fixture = Path(__file__).resolve().parent.parent / "fixtures" / "backups" / "v1" / "manifest.json"
    raw = json.loads(fixture.read_text())
    manifest = Manifest_from_dict(raw)
    assert manifest.manifest_version == CURRENT_MANIFEST_VERSION
    assert manifest.components["planbar_db"].checksum_sha256


def test_manifest_migration_v09_to_v10():
    raw_v09 = {
        "created_at": "2026-07-14T03:00:00Z",
        "tool_version": "0.0.9",
        "tenant": "kunde1",
        "db": {
            "key": "kunde1/20260714-030000/planbar_db.dump",
            "size_bytes": 100,
            "checksum_sha256": "abc",
        },
    }
    migrated = _migrate_v09_to_v10(raw_v09)
    assert migrated["manifest_version"] == "1.0"
    assert "components" in migrated
    assert "planbar_db" in migrated["components"]
    assert migrated["components"]["planbar_db"]["key"].endswith("planbar_db.dump")
    assert migrated["verified"] is False


def test_manifest_migration_v10_to_v20():
    raw_v10 = {
        "manifest_version": "1.0",
        "created_at": "2026-07-14T03:00:00Z",
        "tool_version": "0.1.0",
        "tenant": "kunde1",
        "verified": False,
        "components": {
            "planbar_db": {
                "type": "postgres_dump",
                "format": "custom",
                "key": "kunde1/x/planbar_db.dump",
                "size_bytes": 100,
                "checksum_sha256": "abc",
            },
            "uploads": {
                "type": "tar_gz",
                "key": "kunde1/x/uploads.tar.gz",
                "size_bytes": 10,
                "checksum_sha256": "def",
            },
        },
    }
    migrated = _migrate_v10_to_v20(raw_v10)
    assert migrated["manifest_version"] == "2.0"
    for component in migrated["components"].values():
        assert "encryption" in component
        assert "compression" in component
    # Default-Werte: encryption = none, compression = none
    assert migrated["components"]["planbar_db"]["encryption"] == "none"
    assert migrated["components"]["uploads"]["compression"] == "none"


def test_manifest_migration_chain_three_steps():
    # v0.9 -> 1.0 -> 2.0 in einem Durchlauf via Manifest_from_dict
    raw_v09 = {
        "created_at": "2026-07-14T03:00:00Z",
        "tool_version": "0.0.9",
        "tenant": "kunde1",
        "db": {
            "key": "kunde1/x/planbar_db.dump",
            "size_bytes": 100,
            "checksum_sha256": "abc",
        },
    }
    manifest = Manifest_from_dict(raw_v09)
    assert manifest.manifest_version == "2.0"
    assert "encryption" in manifest.components["planbar_db"].model_dump()


def test_manifest_checksums_per_component():
    manifest = Manifest(
        manifest_version=CURRENT_MANIFEST_VERSION,
        created_at=datetime(2026, 7, 14, 3, 0, 0, tzinfo=timezone.utc),
        tool_version="0.1.0",
        tenant="kunde1",
        verified=False,
        components={
            "a": ComponentEntry(type="x", key="a", size_bytes=1, checksum_sha256="h1"),
            "b": ComponentEntry(type="x", key="b", size_bytes=1, checksum_sha256="h2"),
        },
    )
    dumped = manifest.to_dict()
    assert dumped["components"]["a"]["checksum_sha256"] == "h1"
    assert dumped["components"]["b"]["checksum_sha256"] == "h2"


def test_manifest_verified_false_after_creation():
    manifest = Manifest(
        manifest_version="1.0",
        created_at=datetime(2026, 7, 14, 3, 0, 0, tzinfo=timezone.utc),
        tool_version="0.1.0",
        tenant="kunde1",
        components={"planbar_db": ComponentEntry(**_make_component())},
    )
    assert manifest.verified is False


def test_manifest_verified_true_after_validation():
    manifest = Manifest(
        manifest_version="1.0",
        created_at=datetime(2026, 7, 14, 3, 0, 0, tzinfo=timezone.utc),
        tool_version="0.1.0",
        tenant="kunde1",
        components={"planbar_db": ComponentEntry(**_make_component())},
    )
    manifest.verified = True
    assert manifest.verified is True
    assert manifest.to_dict()["verified"] is True


def test_manifest_migrators_table_shape():
    # 0.9 und 1.0 müssen in der Dispatch-Tabelle stehen
    assert "0.9" in MANIFEST_MIGRATORS
    assert "1.0" in MANIFEST_MIGRATORS
    assert callable(MANIFEST_MIGRATORS["0.9"])
    assert callable(MANIFEST_MIGRATORS["1.0"])


def test_manifest_from_dict_missing_components():
    # Wenn keine manifest_version gesetzt ist -> v0.9_legacy assumed
    raw = {
        "created_at": "2026-07-14T03:00:00Z",
        "tool_version": "0.0.9",
        "tenant": "kunde1",
    }
    # v0.9 ohne `db`-Block -> Validierungsfehler
    with pytest.raises(ManifestError):
        Manifest_from_dict(raw)


def test_manifest_v2_fixture_loadable():
    fixture = Path(__file__).resolve().parent.parent / "fixtures" / "backups" / "v2" / "manifest.json"
    raw = json.loads(fixture.read_text())
    manifest = Manifest_from_dict(raw)
    assert manifest.manifest_version == "2.0"
    assert manifest.components["planbar_db"].encryption in ("none", "SSE-S3")
