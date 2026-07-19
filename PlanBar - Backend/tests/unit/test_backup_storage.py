"""Tests für `app.backup.storage` – LocalStorage + S3Storage (moto) + Factory."""

import time
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from app.backup.config import StorageType
from app.backup.exceptions import BackupNotFoundError
from app.backup.storage import (
    BackupInfo,
    BackupStorage,
    LocalStorage,
    S3Storage,
    storage_factory,
)


# ---------------------------------------------------------------------------
# LocalStorage
# ---------------------------------------------------------------------------


@pytest.fixture
def local_storage(tmp_path):
    return LocalStorage(root=tmp_path)


def test_local_storage_upload_download(local_storage):
    key = "kunde1/20260714-030000/planbar_db.dump"
    data = b"hello world"
    local_storage.upload(key, data, metadata={"tenant": "kunde1"})
    assert local_storage.download(key) == data


def test_local_storage_atomic_write(local_storage, tmp_path):
    key = "foo/bar.bin"
    local_storage.upload(key, b"data")
    # Kein Halbzeug: tmp-Dateien dürfen nicht übrig bleiben
    leftover = list(tmp_path.rglob("*.tmp"))
    assert leftover == []
    # Ziel existiert
    assert local_storage.exists(key)


def test_local_storage_list_backups(local_storage):
    for i in range(3):
        local_storage.upload(f"kunde1/run{i}/db.dump", b"x")
    page = local_storage.list_backups(prefix="kunde1/")
    assert len(page.items) == 3
    assert page.next_page_token is None


def test_local_storage_list_page_two(local_storage):
    for i in range(5):
        local_storage.upload(f"kunde1/run{i}/db.dump", b"x")
    page = local_storage.list_backups(prefix="kunde1/", page_size=2)
    assert len(page.items) == 2
    assert page.next_page_token is not None
    page2 = local_storage.list_backups(prefix="kunde1/", page_size=2, page_token=page.next_page_token)
    assert len(page2.items) == 2


def test_local_storage_list_backups_pagination(local_storage):
    for i in range(4):
        local_storage.upload(f"kunde1/run{i}/db.dump", b"x")
    seen = []
    token = None
    for _ in range(10):
        page = local_storage.list_backups(prefix="kunde1/", page_size=2, page_token=token)
        seen.extend(page.items)
        if page.next_page_token is None:
            break
        token = page.next_page_token
    assert len(seen) == 4


def test_local_storage_delete(local_storage):
    local_storage.upload("a", b"x")
    local_storage.delete("a")
    assert not local_storage.exists("a")


def test_local_storage_exists(local_storage):
    assert local_storage.exists("missing") is False
    local_storage.upload("there", b"x")
    assert local_storage.exists("there") is True


def test_local_storage_head(local_storage):
    local_storage.upload("h", b"hello", metadata={"tenant": "k1"})
    info = local_storage.head("h")
    assert info.size_bytes == 5
    assert info.metadata.get("tenant") == "k1"
    assert isinstance(info.last_modified, datetime)


def test_local_storage_not_found(local_storage):
    with pytest.raises(BackupNotFoundError):
        local_storage.download("does-not-exist")
    with pytest.raises(BackupNotFoundError):
        local_storage.head("does-not-exist")


def test_local_storage_lock_acquire(local_storage):
    assert local_storage.acquire_lock("lock") is True
    assert local_storage.exists(".locks/lock")


def test_local_storage_lock_contention(local_storage):
    assert local_storage.acquire_lock("lock") is True
    assert local_storage.acquire_lock("lock", ttl_seconds=300) is False


def test_local_storage_lock_release(local_storage):
    assert local_storage.acquire_lock("lock") is True
    local_storage.release_lock("lock")
    assert local_storage.acquire_lock("lock") is True


def test_local_storage_lock_ttl_expiry(local_storage):
    assert local_storage.acquire_lock("lock", ttl_seconds=0) is True
    # ttl_seconds=0 => sofort abgelaufen
    time.sleep(0.01)
    assert local_storage.acquire_lock("lock", ttl_seconds=300) is True


# ---------------------------------------------------------------------------
# S3Storage via moto
# ---------------------------------------------------------------------------


@pytest.fixture
def s3_storage():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="planbar-backups")
        yield S3Storage(
            bucket="planbar-backups",
            region="us-east-1",
            endpoint_url=None,
            access_key_id="x",
            secret_access_key="x",
            path_prefix="",
        )


def test_s3_storage_upload_download(s3_storage):
    s3_storage.upload("kunde1/x.dump", b"hello", metadata={"tenant": "k1"})
    assert s3_storage.download("kunde1/x.dump") == b"hello"


def test_s3_storage_list_backups(s3_storage):
    for i in range(3):
        s3_storage.upload(f"kunde1/run{i}.dump", b"x")
    page = s3_storage.list_backups(prefix="kunde1/")
    assert len(page.items) == 3


def test_s3_storage_list_backups_pagination(s3_storage):
    for i in range(5):
        s3_storage.upload(f"kunde1/run{i}.dump", b"x")
    page = s3_storage.list_backups(prefix="kunde1/", page_size=2)
    assert len(page.items) == 2
    assert page.next_page_token is not None
    page2 = s3_storage.list_backups(prefix="kunde1/", page_size=2, page_token=page.next_page_token)
    assert len(page2.items) == 2


def test_s3_storage_delete(s3_storage):
    s3_storage.upload("kunde1/x.dump", b"x")
    s3_storage.delete("kunde1/x.dump")
    assert not s3_storage.exists("kunde1/x.dump")


def test_s3_storage_metadata(s3_storage):
    s3_storage.upload("kunde1/x.dump", b"x", metadata={"tenant": "k1", "ver": "1"})
    info = s3_storage.head("kunde1/x.dump")
    assert info.metadata.get("tenant") == "k1"
    assert info.metadata.get("ver") == "1"


def test_s3_storage_lock_acquire(s3_storage):
    assert s3_storage.acquire_lock("lock") is True


def test_s3_storage_lock_contention(s3_storage):
    assert s3_storage.acquire_lock("lock") is True
    assert s3_storage.acquire_lock("lock") is False


def test_s3_storage_lock_release(s3_storage):
    assert s3_storage.acquire_lock("lock") is True
    s3_storage.release_lock("lock")
    assert s3_storage.acquire_lock("lock") is True


def test_s3_storage_not_found(s3_storage):
    with pytest.raises(BackupNotFoundError):
        s3_storage.head("missing")
    with pytest.raises(BackupNotFoundError):
        s3_storage.download("missing")


def test_s3_storage_checksum_metadata(s3_storage):
    s3_storage.upload("k/x.dump", b"hello", metadata={"checksum_sha256": "abc"})
    info = s3_storage.head("k/x.dump")
    assert info.checksum_sha256 == "abc"
    assert info.size_bytes == 5


# ---------------------------------------------------------------------------
# Contract + Factory
# ---------------------------------------------------------------------------


def test_storage_interface_contract(local_storage, s3_storage):
    """Beide Storages erfüllen denselben Basisvertrag."""
    for storage in (local_storage, s3_storage):
        assert isinstance(storage, BackupStorage)
        storage.upload("contract/key", b"data", metadata={"k": "v"})
        assert storage.exists("contract/key")
        assert storage.download("contract/key") == b"data"
        info = storage.head("contract/key")
        assert info.size_bytes == 4
        assert info.key == "contract/key"
        page = storage.list_backups(prefix="contract/")
        assert len(page.items) == 1
        storage.delete("contract/key")
        assert not storage.exists("contract/key")


def test_storage_factory_local():
    storage = storage_factory(StorageType.LOCAL, local_dir=Path("/tmp/x"))
    assert isinstance(storage, LocalStorage)


def test_storage_factory_s3():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="planbar-factory")
        storage = storage_factory(
            StorageType.S3,
            s3_bucket="planbar-factory",
            s3_region="us-east-1",
            access_key_id="x",
            secret_access_key="x",
            endpoint_url=None,
        )
        assert isinstance(storage, S3Storage)


def test_storage_factory_unknown():
    with pytest.raises(ValueError):
        storage_factory("invalid")  # type: ignore[arg-type]


def test_backup_info_dataclass():
    info = BackupInfo(
        key="k",
        size_bytes=10,
        last_modified=datetime(2026, 7, 14, 3, 0, 0, tzinfo=timezone.utc),
        metadata={},
        checksum_sha256=None,
    )
    assert info.key == "k"
    assert info.size_bytes == 10
