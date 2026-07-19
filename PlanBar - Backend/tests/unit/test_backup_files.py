"""Tests für ``app.backup.files`` (Upload-Archivierung)."""

from __future__ import annotations

import io
import tarfile

from app.backup.files import FilesBackup, archive_directory, extract_archive


def test_archive_uploads_directory(tmp_path):
    uploads = tmp_path / "uploads"
    (uploads / "pinboard").mkdir(parents=True)
    (uploads / "pinboard" / "a.txt").write_bytes(b"alpha")
    (uploads / "pinboard" / "b.txt").write_bytes(b"beta")

    fb = FilesBackup(source=uploads / "pinboard")
    archive = fb.archive()
    assert isinstance(archive, bytes)
    assert len(archive) > 0


def test_archive_empty_directory(tmp_path):
    src = tmp_path / "empty"
    src.mkdir()
    archive = archive_directory(src)
    assert isinstance(archive, bytes)
    # Tar-File leer aber gültig
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        names = tar.getnames()
    assert names == []


def test_archive_preserves_structure(tmp_path):
    src = tmp_path / "src"
    (src / "sub" / "deep").mkdir(parents=True)
    (src / "top.txt").write_bytes(b"top")
    (src / "sub" / "mid.txt").write_bytes(b"mid")
    (src / "sub" / "deep" / "lower.txt").write_bytes(b"low")

    archive = archive_directory(src)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        names = {m.name for m in tar.getmembers()}
    # Relative Pfade (kein führender ``/``)
    assert "top.txt" in names
    assert "sub/mid.txt" in names
    assert "sub/deep/lower.txt" in names


def test_extract_archive(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_bytes(b"hello")

    archive = archive_directory(src)
    target = tmp_path / "out"
    target.mkdir()
    extract_archive(archive, target)
    assert (target / "file.txt").read_bytes() == b"hello"


def test_backup_with_ignored_patterns(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "keep.txt").write_bytes(b"keep")
    (src / "ignore.log").write_bytes(b"ignore me")
    (src / "ignore.tmp").write_bytes(b"temp")

    fb = FilesBackup(source=src, ignore_patterns=["*.log", "*.tmp"])
    archive = fb.archive()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        names = {m.name for m in tar.getmembers()}
    assert "keep.txt" in names
    assert "ignore.log" not in names
    assert "ignore.tmp" not in names


def test_files_backup_roundtrip(tmp_path):
    src = tmp_path / "src"
    (src / "a").mkdir(parents=True)
    (src / "a" / "x.txt").write_bytes(b"1")
    (src / "b.txt").write_bytes(b"2")

    archive = FilesBackup(source=src).archive()
    out = tmp_path / "out"
    out.mkdir()
    FilesBackup.extract_to(archive, out)
    assert (out / "a" / "x.txt").read_bytes() == b"1"
    assert (out / "b.txt").read_bytes() == b"2"
