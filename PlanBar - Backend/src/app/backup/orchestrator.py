"""Orchestriert ``backup_all`` / ``restore_all`` inkl. Locking, Verify & Retention."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from app.backup.config import BackupConfig
from app.backup.database import DatabaseBackup, dump_database, restore_database
from app.backup.exceptions import BackupLockError, BackupNotFoundError, BackupRestoreError
from app.backup.files import FilesBackup
from app.backup.metadata import CURRENT_MANIFEST_VERSION, ComponentEntry, Manifest, Manifest_from_dict
from app.backup.storage import BackupStorage

logger = logging.getLogger(__name__)

TOOL_VERSION = "0.2.0"

# Restore-Reihenfolge (Plan Abschnitt 3.6)
COMPONENT_ORDER_RESTORE: tuple[str, ...] = (
    "config",
    "migrations",
    "planbar_db",
    "tito_db",
    "uploads",
)

# Backup-Reihenfolge (gleich aus Convenience, abweichend von Restore)
COMPONENT_ORDER_BACKUP: tuple[str, ...] = (
    "planbar_db",
    "tito_db",
    "uploads",
    "config",
    "migrations",
)

_DEFAULT_EXT = {
    "planbar_db": "planbar_db.dump",
    "tito_db": "tito_db.dump",
    "uploads": "uploads.tar.gz",
    "config": "config.tar.gz",
    "migrations": "migrations.tar.gz",
}

_DEFAULT_TYPE = {
    "planbar_db": "postgres_dump",
    "tito_db": "postgres_dump",
    "uploads": "tar_gz",
    "config": "env_dir",
    "migrations": "directory_archive",
}


class Orchestrator:
    """Orchestriert einen kompletten Backup- oder Restore-Lauf."""

    def __init__(
        self,
        config: BackupConfig,
        storage: BackupStorage,
        *,
        now: Callable[[], datetime] | None = None,
        alembic_runner: Callable[[str, str], None] | None = None,
        current_schema_version: str | None = None,
        migrations_dir: Path | None = None,
        component_providers: dict[str, Callable[[], bytes]] | None = None,
    ):
        self.config = config
        self.storage = storage
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.alembic_runner = alembic_runner
        self.current_schema_version = current_schema_version
        self.migrations_dir = migrations_dir or (
            Path(__file__).resolve().parent.parent.parent.parent / "migrations" / "versions"
        )
        self._component_providers = component_providers or {}
        self.last_errors: list[tuple[str, str]] = []

    # ----------------------------------------------------------------- helpers

    def _alembic_version_for(self, name: str) -> str | None:
        url = self.config.db_url_planbar if name == "planbar_db" else self.config.db_url_tito
        if not url:
            return None
        try:
            return DatabaseBackup(db_url=url).get_alembic_current_version()
        except Exception:
            return None

    def _generate_default(self, name: str) -> bytes | None:
        if name == "planbar_db":
            url = self.config.db_url_planbar
            if not url:
                return None
            return dump_database(DatabaseBackup(db_url=url))
        if name == "tito_db":
            url = self.config.db_url_tito
            if not url:
                return None
            return dump_database(DatabaseBackup(db_url=url))
        if name == "uploads":
            if not self.config.uploads_dir:
                return None
            return FilesBackup(source=Path(self.config.uploads_dir)).archive()
        if name == "config":
            if not self.config.config_dir:
                return None
            return FilesBackup(source=Path(self.config.config_dir)).archive()
        if name == "migrations":
            if not self.config.include_migrations:
                return None
            if not self.migrations_dir or not Path(self.migrations_dir).exists():
                return None
            return DatabaseBackup(db_url=self.config.db_url_planbar or "sqlite:///:memory:").archive_migrations_dir(
                migrations_dir=Path(self.migrations_dir)
            )
        return None

    # --------------------------------------------------------------- backup

    def backup_all(
        self,
        tenant: str,
        *,
        components: Iterable[str] | None = None,
        dry_run: bool = False,
        verify: bool | None = None,
    ) -> Manifest:
        if not dry_run:
            if not self.storage.acquire_lock("backup", ttl_seconds=self.config.lock_ttl_seconds):
                raise BackupLockError("could not acquire backup lock")
        try:
            comp_list = list(components) if components is not None else list(COMPONENT_ORDER_BACKUP)
            ts = self.now().strftime("%Y%m%d-%H%M%S")
            prefix = f"{tenant}/{ts}"
            manifest = Manifest(
                manifest_version=CURRENT_MANIFEST_VERSION,
                created_at=self.now(),
                tool_version=TOOL_VERSION,
                tenant=tenant,
                verified=False,
                components={},
            )
            self.last_errors = []
            for name in comp_list:
                if name == "migrations" and not self.config.include_migrations:
                    continue
                try:
                    if name in self._component_providers:
                        data = self._component_providers[name]()
                    else:
                        data = self._generate_default(name)
                    if data is None:
                        continue
                    key = f"{prefix}/{_DEFAULT_EXT[name]}"
                    checksum = hashlib.sha256(data).hexdigest()
                    extra: dict[str, Any] = {}
                    if name in ("planbar_db", "tito_db"):
                        alembic_ver = self._alembic_version_for(name)
                        if alembic_ver:
                            extra["alembic_version"] = alembic_ver
                            try:
                                db = DatabaseBackup(
                                    db_url=self.config.db_url_planbar
                                    if name == "planbar_db"
                                    else self.config.db_url_tito
                                )
                                extra["migration_history"] = db.get_alembic_migration_history(
                                    migrations_dir=self.migrations_dir
                                )
                            except Exception:
                                pass
                    comp = ComponentEntry(
                        type=_DEFAULT_TYPE[name],
                        format="custom" if name in ("planbar_db", "tito_db") else None,
                        key=key,
                        size_bytes=len(data),
                        checksum_sha256=checksum,
                        **extra,
                    )
                    if not dry_run:
                        self.storage.upload(
                            key,
                            data,
                            metadata={"checksum_sha256": checksum, "component": name},
                        )
                    manifest.components[name] = comp
                except Exception as exc:
                    logger.exception("component %s failed", name)
                    self.last_errors.append((name, str(exc)))
            do_verify = verify if verify is not None else self.config.verify_upload
            if do_verify and not dry_run and manifest.components:
                manifest.verified = self.verify_manifest(manifest)
            if not dry_run:
                manifest_key = f"{prefix}/manifest.json"
                self.storage.upload(
                    manifest_key,
                    json.dumps(manifest.to_dict()).encode("utf-8"),
                    metadata={"manifest": "true"},
                )
            return manifest
        finally:
            if not dry_run:
                self.storage.release_lock("backup")

    def verify_manifest(self, manifest: Manifest) -> bool:
        """Lädt jede Komponente neu herunter und prüft die SHA256-Checksum."""
        for name, comp in manifest.components.items():
            try:
                data = self.storage.download(comp.key)
            except BackupNotFoundError:
                return False
            if comp.checksum_sha256 is None:
                return False
            if hashlib.sha256(data).hexdigest() != comp.checksum_sha256:
                return False
        return True

    def apply_retention(self, tenant: str, *, now: datetime | None = None) -> list[str]:
        """Loescht Backups aelter als ``config.retention_days``.

        Gibt die Liste geloeschter Storage-Keys zurueck.
        """
        if callable(now):
            now = now()
        if now is None:
            now = self.now()
        cutoff = now - timedelta(days=self.config.retention_days)
        deleted: list[str] = []
        prefix = f"{tenant}/"
        token: str | None = None
        manifests: list[tuple[datetime, str]] = []
        # 1. Alle manifest.json auflisten
        while True:
            page = self.storage.list_backups(prefix=prefix, page_size=100, page_token=token)
            for item in page.items:
                if item.key.endswith("/manifest.json"):
                    try:
                        raw = self.storage.download(item.key)
                        data = json.loads(raw)
                        created = data.get("created_at")
                        if created:
                            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                            manifests.append((created_dt, "/".join(item.key.split("/")[:-1])))
                    except Exception:
                        continue
            if page.next_page_token is None:
                break
            token = page.next_page_token
        # 2. Alte Faelle identifizieren und Komponenten loeschen
        for created, sub_prefix in manifests:
            if created < cutoff:
                tok: str | None = None
                while True:
                    page = self.storage.list_backups(prefix=sub_prefix + "/", page_size=200, page_token=tok)
                    for item in page.items:
                        self.storage.delete(item.key)
                        deleted.append(item.key)
                    if page.next_page_token is None:
                        break
                    tok = page.next_page_token
        return deleted

    # --------------------------------------------------------------- restore

    def restore_all(
        self,
        *,
        manifest: Manifest | None = None,
        manifest_key: str | None = None,
        components: Iterable[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if manifest is None and manifest_key is None:
            raise ValueError("manifest or manifest_key required")
        if manifest is None:
            raw = self.storage.download(manifest_key)  # type: ignore[arg-type]
            manifest = Manifest_from_dict(json.loads(raw))
        wanted = list(components) if components is not None else list(COMPONENT_ORDER_RESTORE)
        if dry_run:
            return {"dry_run": True, "planned": list(manifest.components.keys())}
        restored: list[str] = []
        for name in COMPONENT_ORDER_RESTORE:
            if name not in wanted:
                continue
            if name not in manifest.components:
                if components is not None:
                    raise BackupRestoreError(f"component {name} missing in manifest")
                continue
            comp = manifest.components[name]
            try:
                data = self.storage.download(comp.key)
            except BackupNotFoundError as exc:
                raise BackupRestoreError(f"missing object for {name}") from exc
            if name in ("planbar_db", "tito_db"):
                self._restore_db_component(name, comp, data)
            elif name in ("uploads", "config"):
                self._restore_files_component(name, comp, data)
            elif name == "migrations":
                self._restore_migrations_component(name, comp, data)
            restored.append(name)
        return {"restored": restored}

    def _restore_db_component(self, name: str, component: ComponentEntry, data: bytes) -> None:
        url = self.config.db_url_planbar if name == "planbar_db" else self.config.db_url_tito
        if not url:
            raise BackupRestoreError(f"no db url configured for {name}")
        db = DatabaseBackup(db_url=url)
        restore_database(db, data)
        # Schema-Evolution: ggf. alembic upgrade
        dump_version = component.alembic_version or component.schema_version
        if dump_version and self.current_schema_version and dump_version != self.current_schema_version:
            if self.alembic_runner is not None:
                logger.info(
                    "schema mismatch %s -> %s, running alembic upgrade", dump_version, self.current_schema_version
                )
                self.alembic_runner(url, self.current_schema_version)

    def _restore_files_component(self, name: str, component: ComponentEntry, data: bytes) -> None:
        if name == "uploads":
            target = self.config.uploads_dir
        else:
            target = self.config.config_dir
        if not target:
            raise BackupRestoreError(f"no target dir configured for {name}")
        Path(target).mkdir(parents=True, exist_ok=True)
        FilesBackup.extract_to(data, Path(target))

    def _restore_migrations_component(self, name: str, component: ComponentEntry, data: bytes) -> None:
        if self.migrations_dir is None:
            return
        target = Path(self.migrations_dir)
        target.mkdir(parents=True, exist_ok=True)
        FilesBackup.extract_to(data, target)

    # ----------------------------------------------------------- legacy dump

    def describe_backup(self, dump_key: str) -> dict[str, Any]:
        """Beschreibt ein Backup-Verzeichnis; liefert Default-Metadaten bei Legacy."""
        prefix = "/".join(dump_key.split("/")[:-1])
        manifest_key = f"{prefix}/manifest.json"
        if self.storage.exists(manifest_key):
            raw = self.storage.download(manifest_key)
            manifest = Manifest_from_dict(json.loads(raw))
            return {
                "has_manifest": True,
                "manifest": manifest.to_dict(),
                "checksum_sha256": None,
            }
        return {
            "has_manifest": False,
            "checksum_sha256": None,
            "components": {"planbar_db": dump_key},
        }

    def restore_legacy(self, dump_key: str) -> dict[str, Any]:
        """Stellt einen einzelnen, ggf. manifest-losen Dump wieder her."""
        info = self.describe_backup(dump_key)
        if info["has_manifest"]:
            manifest = Manifest_from_dict(info["manifest"])
            return self.restore_all(manifest=manifest, components=["planbar_db"])
        # Kein Manifest -> Default-Restore
        data = self.storage.download(dump_key)
        if not self.config.db_url_planbar:
            raise BackupRestoreError("no db_url_planbar configured")
        comp = ComponentEntry(
            type="postgres_dump",
            key=dump_key,
            size_bytes=len(data),
            checksum_sha256=None,
        )
        self._restore_db_component("planbar_db", comp, data)
        return {"restored": ["planbar_db"]}
