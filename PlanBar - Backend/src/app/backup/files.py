"""Datei-Archivierung (uploads/, config/).

Verwendet ``tarfile``内置, mit optionalen Ignore-Patterns (fnmatch).
"""

from __future__ import annotations

import fnmatch
import io
import tarfile
from pathlib import Path


def archive_directory(source: Path, ignore_patterns: list[str] | None = None) -> bytes:
    """Packt ein Verzeichnis rekursiv als ``.tar.gz`` mit *relativen* Pfaden."""
    source = Path(source)
    patterns = ignore_patterns or []
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        if source.exists():
            for path in sorted(source.rglob("*")):
                if path.is_dir():
                    continue
                rel = path.relative_to(source).as_posix()
                if any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(path.name, pat) for pat in patterns):
                    continue
                tar.add(path, arcname=rel)
    return buffer.getvalue()


def extract_archive(archive_bytes: bytes, target: Path) -> None:
    """Entpackt ein ``.tar.gz``-Archiv in ein Zielverzeichnis."""
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
        for member in tar.getmembers():
            # Safe member check: keine absoluten Pfade, kein ``..``
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                continue
            tar.extract(member, path=target)


class FilesBackup:
    """Kapselt Archivierung/Extraktion eines Verzeichnisses."""

    def __init__(self, source: Path, ignore_patterns: list[str] | None = None):
        self.source = Path(source)
        self.ignore_patterns = ignore_patterns or []

    def archive(self) -> bytes:
        return archive_directory(self.source, ignore_patterns=self.ignore_patterns)

    @staticmethod
    def extract_to(archive_bytes: bytes, target: Path) -> None:
        extract_archive(archive_bytes, target)
