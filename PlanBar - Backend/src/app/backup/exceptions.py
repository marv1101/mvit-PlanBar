"""Domain-Exceptions für das Backup-Modul."""

from __future__ import annotations


class BackupError(Exception):
    """Basisklasse für alle Backup-Fehler."""


class BackupNotFoundError(BackupError):
    """Ein Backup-Objekt existiert nicht unter dem angegebenen Key."""


class BackupLockError(BackupError):
    """Ein Distributed Lock konnte nicht akquiriert werden."""


class BackupRestoreError(BackupError):
    """Fehler während eines Restore-Laufs."""


class BackupVerificationError(BackupError):
    """Eine Checksum-Prüfung ist fehlgeschlagen."""


class ManifestError(BackupError):
    """Ein Manifest ist ungültig oder nicht lesbar."""
