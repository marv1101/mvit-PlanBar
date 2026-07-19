"""Storage-Interface (Strategy) + Local- und S3-Implementierungen.

Beide Implementierungen teilen sich einen gemeinsamen Contract
(``BackupStorage``). Paginierung ist zwingend, weil über Jahre tausende
Backup-Objekte auflaufen. Locking verhindert parallele Backup-Läufe:

* ``LocalStorage``: Lock-Datei im Unterverzeichnis ``.locks/`` mit mtime-TTL.
* ``S3Storage``: Conditional-Put (If-None-Match: '*') als Distributed Lock.
"""

from __future__ import annotations

import os
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.backup.exceptions import BackupNotFoundError


# ---------------------------------------------------------------------------
# Datentrukturen
# ---------------------------------------------------------------------------


@dataclass
class BackupInfo:
    key: str
    size_bytes: int
    last_modified: datetime
    metadata: dict[str, str] = field(default_factory=dict)
    checksum_sha256: str | None = None


@dataclass
class BackupListPage:
    items: list[BackupInfo]
    next_page_token: str | None


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


class BackupStorage(ABC):
    """Storage-Strategy für Backup-Objekte."""

    @abstractmethod
    def upload(self, key: str, data: bytes, metadata: dict | None = None) -> str: ...

    @abstractmethod
    def download(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def head(self, key: str) -> BackupInfo: ...

    @abstractmethod
    def list_backups(
        self,
        prefix: str,
        *,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> BackupListPage: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def acquire_lock(self, lock_key: str, ttl_seconds: int = 300) -> bool: ...

    @abstractmethod
    def release_lock(self, lock_key: str) -> None: ...


# ---------------------------------------------------------------------------
# LocalStorage
# ---------------------------------------------------------------------------


class LocalStorage(BackupStorage):
    """Dateisystem-basierte Storage-Implementierung."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / ".locks").mkdir(exist_ok=True)

    # --- Hilfsfunktionen ---------------------------------------------------

    def _path(self, key: str) -> Path:
        return self.root / key

    @staticmethod
    def _normalize_prefix(prefix: str) -> str:
        return prefix.lstrip("/")

    # --- Storage-Operationen -----------------------------------------------

    def upload(self, key: str, data: bytes, metadata: dict | None = None) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: tmp -> rename
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".part")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        # Metadata Sidecar (.meta.json)
        if metadata:
            meta_path = path.with_suffix(path.suffix + ".meta.json")
            import json

            meta_path.write_text(json.dumps(metadata))
        return key

    def download(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise BackupNotFoundError(key)
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def head(self, key: str) -> BackupInfo:
        path = self._path(key)
        if not path.exists():
            raise BackupNotFoundError(key)
        meta_path = path.with_suffix(path.suffix + ".meta.json")
        metadata: dict[str, str] = {}
        if meta_path.exists():
            import json

            metadata = json.loads(meta_path.read_text() or "{}")
        stat = path.stat()
        return BackupInfo(
            key=key,
            size_bytes=stat.st_size,
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            metadata=metadata,
            checksum_sha256=metadata.get("checksum_sha256"),
        )

    def list_backups(
        self,
        prefix: str,
        *,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> BackupListPage:
        prefix_norm = self._normalize_prefix(prefix)
        base = self.root / prefix_norm
        if not base.exists():
            return BackupListPage(items=[], next_page_token=None)
        if base.is_file():
            items = [self.head(prefix_norm)]
            return BackupListPage(items=items, next_page_token=None)
        # Walk inside base
        all_keys: list[str] = []
        for p in base.rglob("*"):
            if p.is_file() and ".locks" not in p.parts and ".meta.json" not in p.name:
                rel = p.relative_to(self.root).as_posix()
                all_keys.append(rel)
        all_keys.sort()
        if page_token:
            try:
                start = all_keys.index(page_token) + 1
            except ValueError:
                start = 0
        else:
            start = 0
        slice_ = all_keys[start : start + page_size]
        items = [self.head(k) for k in slice_]
        next_token = None
        if start + page_size < len(all_keys):
            next_token = all_keys[start + page_size - 1]
        return BackupListPage(items=items, next_page_token=next_token)

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()
        meta_path = path.with_suffix(path.suffix + ".meta.json")
        if meta_path.exists():
            meta_path.unlink()

    # --- Locking ------------------------------------------------------------

    def _lock_path(self, lock_key: str) -> Path:
        return self.root / ".locks" / lock_key

    def acquire_lock(self, lock_key: str, ttl_seconds: int = 300) -> bool:
        path = self._lock_path(lock_key)
        if path.exists():
            try:
                content = path.read_text()
                expiry = float(content.split(":", 1)[1])
            except (ValueError, IndexError, OSError):
                expiry = 0.0
            if time.time() < expiry:
                return False
            path.unlink(missing_ok=True)
        # Atomarer Versuch via os.O_CREAT|O_EXCL
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        try:
            expiry = time.time() + ttl_seconds
            os.write(fd, f"{uuid.uuid4()}:{expiry}".encode())
        finally:
            os.close(fd)
        return True

    def release_lock(self, lock_key: str) -> None:
        self._lock_path(lock_key).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# S3Storage
# ---------------------------------------------------------------------------


class S3Storage(BackupStorage):
    """S3-kompatible Object-Storage-Implementierung via boto3."""

    def __init__(
        self,
        bucket: str,
        region: str,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        path_prefix: str = "",
    ):
        import boto3

        self.bucket = bucket
        self.path_prefix = path_prefix.strip("/") if path_prefix else ""
        self._client = boto3.client(
            "s3",
            region_name=region or "us-east-1",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    # --- Hilfsfunktionen ---------------------------------------------------

    def _full_key(self, key: str) -> str:
        if self.path_prefix:
            return f"{self.path_prefix}/{key.lstrip('/')}"
        return key.lstrip("/")

    def _strip_prefix(self, key: str) -> str:
        if self.path_prefix and key.startswith(self.path_prefix + "/"):
            return key[len(self.path_prefix) + 1 :]
        return key

    @staticmethod
    def _sanitize_metadata(metadata: dict | None) -> dict[str, str]:
        if not metadata:
            return {}
        out: dict[str, str] = {}
        for k, v in metadata.items():
            if v is None:
                continue
            out[str(k)] = str(v)
        return out

    # --- Storage-Operationen -----------------------------------------------

    def upload(self, key: str, data: bytes, metadata: dict | None = None) -> str:
        full = self._full_key(key)
        self._client.put_object(
            Bucket=self.bucket,
            Key=full,
            Body=data,
            Metadata=self._sanitize_metadata(metadata),
        )
        return key

    def download(self, key: str) -> bytes:
        full = self._full_key(key)
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=full)
        except Exception as exc:
            if "NoSuchKey" in type(exc).__name__ or "404" in str(exc):
                raise BackupNotFoundError(key) from exc
            raise
        return resp["Body"].read()

    def exists(self, key: str) -> bool:
        full = self._full_key(key)
        try:
            self._client.head_object(Bucket=self.bucket, Key=full)
            return True
        except Exception:
            return False

    def head(self, key: str) -> BackupInfo:
        full = self._full_key(key)
        try:
            resp = self._client.head_object(Bucket=self.bucket, Key=full)
        except Exception as exc:
            raise BackupNotFoundError(key) from exc
        metadata = resp.get("Metadata", {}) or {}
        last_modified = resp.get("LastModified")
        if isinstance(last_modified, datetime):
            parsed = last_modified
        else:
            parsed = datetime.now(tz=timezone.utc)
        return BackupInfo(
            key=key,
            size_bytes=int(resp.get("ContentLength", 0)),
            last_modified=parsed,
            metadata=dict(metadata),
            checksum_sha256=metadata.get("checksum_sha256"),
        )

    def list_backups(
        self,
        prefix: str,
        *,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> BackupListPage:
        full_prefix = self._full_key(prefix.lstrip("/"))
        if full_prefix and not full_prefix.endswith("/"):
            full_prefix = full_prefix + "/"
        kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "Prefix": full_prefix,
            "MaxKeys": page_size,
        }
        if page_token:
            kwargs["ContinuationToken"] = page_token
        resp = self._client.list_objects_v2(**kwargs)
        items = []
        for obj in resp.get("Contents", []) or []:
            stripped = self._strip_prefix(obj["Key"])
            lm = obj.get("LastModified")
            if isinstance(lm, datetime):
                last_modified = lm
            else:
                last_modified = datetime.now(tz=timezone.utc)
            items.append(
                BackupInfo(
                    key=stripped,
                    size_bytes=int(obj.get("Size", 0)),
                    last_modified=last_modified,
                    metadata={},
                )
            )
        next_token = resp.get("NextContinuationToken")
        return BackupListPage(items=items, next_page_token=next_token or None)

    def delete(self, key: str) -> None:
        full = self._full_key(key)
        self._client.delete_object(Bucket=self.bucket, Key=full)

    # --- Locking ------------------------------------------------------------

    def acquire_lock(self, lock_key: str, ttl_seconds: int = 300) -> bool:
        full = self._full_key(f".locks/{lock_key}")
        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=full,
                Body=str(uuid.uuid4()).encode(),
                IfNoneMatch="*",
            )
            return True
        except Exception as exc:
            # Conditional put fehlgeschlagen -> Lock bereits gehalten
            from botocore.exceptions import ClientError

            if isinstance(exc, ClientError) and exc.response.get("Error", {}).get("Code") in (
                "PreconditionFailed",
                "409",
            ):
                return False
            raise

    def release_lock(self, lock_key: str) -> None:
        full = self._full_key(f".locks/{lock_key}")
        try:
            self._client.delete_object(Bucket=self.bucket, Key=full)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def storage_factory(storage_type, **kwargs) -> BackupStorage:
    from app.backup.config import StorageType

    if storage_type == StorageType.LOCAL:
        return LocalStorage(root=Path(kwargs["local_dir"]))
    if storage_type == StorageType.S3:
        return S3Storage(
            bucket=kwargs["s3_bucket"],
            region=kwargs.get("s3_region") or "us-east-1",
            endpoint_url=kwargs.get("s3_endpoint"),
            access_key_id=kwargs.get("s3_access_key_id"),
            secret_access_key=kwargs.get("s3_secret_access_key"),
            path_prefix=kwargs.get("s3_path_prefix", ""),
        )
    raise ValueError(f"unknown storage type: {storage_type!r}")
