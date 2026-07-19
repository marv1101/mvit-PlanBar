"""Public API des Backup-Moduls.

Importiert die wichtigsten Symbole, so dass Aufrufer ``from app.backup import
Orchestrator`` schreiben koennen, ohne interne Pfade zu kennen.
"""

from __future__ import annotations

from app.backup.config import BackupConfig, StorageType
from app.backup.exceptions import (
    BackupError,
    BackupLockError,
    BackupNotFoundError,
    BackupRestoreError,
    BackupVerificationError,
    ManifestError,
)
from app.backup.metadata import (
    CURRENT_MANIFEST_VERSION,
    ComponentEntry,
    Manifest,
    Manifest_from_dict,
)
from app.backup.orchestrator import Orchestrator, TOOL_VERSION
from app.backup.storage import (
    BackupInfo,
    BackupListPage,
    BackupStorage,
    LocalStorage,
    S3Storage,
    storage_factory,
)

__all__ = [
    "BackupConfig",
    "StorageType",
    "BackupError",
    "BackupLockError",
    "BackupNotFoundError",
    "BackupRestoreError",
    "BackupVerificationError",
    "ManifestError",
    "CURRENT_MANIFEST_VERSION",
    "ComponentEntry",
    "Manifest",
    "Manifest_from_dict",
    "Orchestrator",
    "TOOL_VERSION",
    "BackupInfo",
    "BackupListPage",
    "BackupStorage",
    "LocalStorage",
    "S3Storage",
    "storage_factory",
]
