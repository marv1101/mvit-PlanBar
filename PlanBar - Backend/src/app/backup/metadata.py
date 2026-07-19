"""Backup-Manifest: versioniertes, selbstbeschreibendes JSON.

Das Manifest ist die zentrale Datenstruktur des Backup-Moduls. Es beschreibt,
welche Komponenten in einem Backup-Lauf gesichert wurden, zu welcher
Schema-Version und mit welchen Prüfsummen. Es wird selbst als JSON-Datei
im Backup abgelegt (Key: ``<prefix>/manifest.json``).

Manifest-Versionen
-------------------

* ``0.9``  – Legacy ohne ``manifest_version``-Feld; nur ein ``db``-Block.
* ``1.0``  – Erste versionierte Form; ``components``-Dict mit allen Komponenten.
* ``2.0``  – Zusätzlich ``encryption`` + ``compression`` pro Komponente.

Jede Versionsänderung braucht einen Migrator (pure function ``dict -> dict``).
Beim Laden eines Manifests wandert ``Manifest_from_dict`` entlang der
Dispatch-Tabelle, bis die aktuelle Version erreicht ist.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, ValidationError

from app.backup.exceptions import ManifestError

CURRENT_MANIFEST_VERSION = "2.0"


class ComponentEntry(BaseModel):
    """Eine einzelne Komponente innerhalb eines Manifests."""

    model_config = ConfigDict(extra="allow")

    type: str
    format: str | None = None
    key: str
    size_bytes: int | None = None
    checksum_sha256: str | None = None

    # DB-bezogene Felder
    alembic_version: str | None = None
    migration_history: list[str] | None = None
    schema_version: str | None = None

    # v2.0-Erweiterungen
    encryption: str = "none"
    compression: str = "none"


class Manifest(BaseModel):
    """Das vollständige Manifest eines Backup-Laufs."""

    model_config = ConfigDict(extra="allow")

    manifest_version: str
    created_at: datetime
    tool_version: str
    tenant: str
    verified: bool = False
    components: dict[str, ComponentEntry]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Migrationen
# ---------------------------------------------------------------------------


def _migrate_v09_to_v10(raw: dict) -> dict:
    """v0.9 (legacy ``db``-Block) -> v1.0 (``components``-Dict).

    Der Legacy-Block sah so aus::

        {"db": {"key": ..., "size_bytes": ..., "checksum_sha256": ...}}

    Er wird in ``components.planbar_db`` überführt.
    """
    if "db" not in raw:
        raise ManifestError("v0.9 manifest has no 'db' block")
    db = raw["db"]
    new = {k: v for k, v in raw.items() if k != "db"}
    new["manifest_version"] = "1.0"
    new.setdefault("verified", False)
    new["components"] = {
        "planbar_db": {
            "type": "postgres_dump",
            "format": "custom",
            "key": db["key"],
            "size_bytes": db.get("size_bytes"),
            "checksum_sha256": db.get("checksum_sha256"),
        }
    }
    return new


def _migrate_v10_to_v20(raw: dict) -> dict:
    """v1.0 -> v2.0: ``encryption`` + ``compression`` pro Komponente."""
    new = dict(raw)
    new["manifest_version"] = "2.0"
    new_components = {}
    for name, component in raw.get("components", {}).items():
        component = dict(component)
        component.setdefault("encryption", "none")
        component.setdefault("compression", "none")
        new_components[name] = component
    new["components"] = new_components
    return new


MANIFEST_MIGRATORS: dict[str, Callable[[dict], dict]] = {
    "0.9": _migrate_v09_to_v10,
    "1.0": _migrate_v10_to_v20,
}


def Manifest_from_dict(raw: dict) -> Manifest:  # noqa: N802 - factory Stil wie pydantic
    """Lädt ein beliebiges Manifest-Dict und migriert es zur aktuellen Version."""
    if not isinstance(raw, dict):
        raise ManifestError("manifest must be a JSON object")
    raw = dict(raw)
    version = raw.get("manifest_version", "0.9")
    while version in MANIFEST_MIGRATORS:
        raw = MANIFEST_MIGRATORS[version](raw)
        version = raw.get("manifest_version", CURRENT_MANIFEST_VERSION)
    if version != CURRENT_MANIFEST_VERSION:
        raise ManifestError(f"unsupported manifest_version: {version}")
    try:
        return Manifest(**raw)
    except ValidationError as exc:
        raise ManifestError(str(exc)) from exc
