"""DB-Dump / Restore mit pg_dump/pg_restore und SQLAlchemy-Fallback.

* Produktiv (PostgreSQL): ``pg_dump``/``pg_restore`` via ``subprocess``
* Dev/Tests (SQLite): SQLAlchemy-basierter JSON-Export ohne pg_dump
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


_REVISION_RE = re.compile(r'^revision\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_DOWN_REVISION_RE = re.compile(r"^down_revision\s*=\s*(.*?)$", re.MULTILINE)


class DatabaseBackup:
    """Kapselt Dump/Restore für eine einzelne Datenbank."""

    def __init__(self, db_url: str):
        self.db_url = db_url

    # --- Hilfsfunktionen ---------------------------------------------------

    def _make_engine(self) -> Engine:
        return create_engine(self.db_url)

    @property
    def _is_sqlite(self) -> bool:
        return self.db_url.startswith("sqlite")

    # --- Alembic -----------------------------------------------------------

    def get_alembic_current_version(self) -> str | None:
        """Liest die aktuelle Revision aus der ``alembic_version``-Tabelle."""
        engine = self._make_engine()
        try:
            inspector = inspect(engine)
            if "alembic_version" not in inspector.get_table_names():
                return None
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                row = result.fetchone()
                if row is None:
                    return None
                return str(row[0])
        finally:
            engine.dispose()

    def get_alembic_migration_history(self, migrations_dir: Path | None = None) -> list[str]:
        """Liefert alle Migrations-IDs in Ketten-Reihenfolge (down_revision -> revision)."""
        if migrations_dir is None:
            migrations_dir = Path(__file__).resolve().parent.parent.parent.parent / "migrations" / "versions"
        revisions: dict[str, str | None] = {}
        for path in sorted(migrations_dir.glob("*.py")):
            if path.name == "__init__.py":
                continue
            content = path.read_text()
            m_rev = _REVISION_RE.search(content)
            if not m_rev:
                continue
            rev = m_rev.group(1)
            m_down = _DOWN_REVISION_RE.search(content)
            if m_down is None:
                revisions[rev] = None
            else:
                raw = m_down.group(1).strip().rstrip(",")
                if raw in ("None", "None,", '""', "''", ""):
                    revisions[rev] = None
                else:
                    revisions[rev] = raw.strip("\"'")
        # Build chain from None-root
        ordered: list[str] = []
        children = {parent: [r for r, p in revisions.items() if p == parent] for parent in [None, *revisions.values()]}
        # Find root(s)
        roots = [r for r, p in revisions.items() if p is None]
        # Walk in deterministic order
        visited: set[str] = set()

        def walk(rev: str):
            if rev in visited:
                return
            visited.add(rev)
            ordered.append(rev)
            for child in sorted(children.get(rev, [])):
                walk(child)

        for r in sorted(roots):
            walk(r)
        return ordered

    # --- Dump (pg_dump) -----------------------------------------------------

    def dump_pg_dump(self) -> bytes:
        """Dump via ``pg_dump`` (produktiver Pfad, PostgreSQL)."""
        cmd = [
            "pg_dump",
            "--format=custom",
            "--compress=9",
            f"--dbname={self.db_url}",
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {result.stderr.decode(errors='replace')}")
        return result.stdout

    # --- Dump (SQLAlchemy Fallback) ----------------------------------------

    def dump_sqlalchemy(self) -> bytes:
        """Dump via SQLAlchemy Reflection – kompatibel mit SQLite/Dev-Umgebungen."""
        engine = self._make_engine()
        try:
            inspector = inspect(engine)
            payload: dict = {
                "alembic_version": None,
                "tables": {},
            }
            # Alembic-Version (optional)
            if "alembic_version" in inspector.get_table_names():
                with engine.connect() as conn:
                    row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                    if row is not None:
                        payload["alembic_version"] = str(row[0])

            for table in sorted(inspector.get_table_names()):
                if table == "alembic_version":
                    continue
                cols_info = inspector.get_columns(table)
                with engine.connect() as conn:
                    rows = conn.execute(text(f'SELECT * FROM "{table}"')).fetchall()
                serialized_rows = []
                for row in rows:
                    serialized_rows.append(
                        {
                            col: row[i]
                            for i, col in enumerate(
                                row._fields if hasattr(row, "_fields") else [c["name"] for c in cols_info]
                            )
                        }
                    )
                payload["tables"][table] = {
                    "columns": [
                        {
                            "name": c["name"],
                            "type": str(c["type"]),
                            "nullable": c.get("nullable", True),
                            "primary_key": False,
                        }
                        for c in cols_info
                    ],
                    "primary_key": inspector.get_pk_constraint(table).get("constrained_columns", []),
                    "rows": serialized_rows,
                }
            return json.dumps(payload, default=str).encode("utf-8")
        finally:
            engine.dispose()

    # --- Restore (pg_restore) ----------------------------------------------

    def restore_pg_restore(self, dump_bytes: bytes) -> None:
        """Restore via ``pg_restore`` (PostgreSQL)."""
        cmd = [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--dbname=" + self.db_url,
        ]
        result = subprocess.run(cmd, input=dump_bytes, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"pg_restore failed: {result.stderr.decode(errors='replace')}")

    # --- Restore (SQLAlchemy Fallback) -------------------------------------

    def restore_sqlalchemy(self, dump_bytes: bytes) -> None:
        """Restore in eine leere DB via SQLAlchemy; Schema wird aus Dump recreated."""
        payload = json.loads(dump_bytes)
        engine = self._make_engine()
        try:
            with engine.begin() as conn:
                # Schema anlegen – Generisches CREATE TABLE pro Komponente
                for table_name, table_info in payload.get("tables", {}).items():
                    cols_ddl: list[str] = []
                    pk = set(table_info.get("primary_key", []))
                    for col in table_info.get("columns", []):
                        col_def = f'"{col["name"]}" {col["type"]}'
                        if not col.get("nullable", True):
                            col_def += " NOT NULL"
                        if col["name"] in pk:
                            col_def += " PRIMARY KEY"
                        cols_ddl.append(col_def)
                    conn.execute(text(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(cols_ddl)})'))
                    # Rows einfügen
                    for row in table_info.get("rows", []):
                        cols = list(row.keys())
                        placeholders = ", ".join(f":{c}" for c in cols)
                        col_list = ", ".join(f'"{c}"' for c in cols)
                        conn.execute(text(f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})'), row)
                # alembic_version-Tabelle + Eintrag
                if payload.get("alembic_version") is not None:
                    conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
                    conn.execute(text("DELETE FROM alembic_version"))
                    conn.execute(
                        text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {"v": payload["alembic_version"]}
                    )
        finally:
            engine.dispose()

    # --- Migrations-Archiv --------------------------------------------------

    def archive_migrations_dir(self, migrations_dir: Path | None = None) -> bytes:
        """Packt das ``versions/``-Verzeichnis der Alembic-Migrationen als tar.gz."""
        if migrations_dir is None:
            migrations_dir = Path(__file__).resolve().parent.parent.parent.parent / "migrations" / "versions"
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            for path in sorted(migrations_dir.glob("*.py")):
                tar.add(path, arcname=path.name)
        return buffer.getvalue()


# ---------------------------------------------------------------------------
# Dispatch-Funktionen
# ---------------------------------------------------------------------------


def dump_database(db: DatabaseBackup) -> bytes:
    """Wählt je nach URL-Schema pg_dump vs. SQLAlchemy-Fallback."""
    if db._is_sqlite:
        return db.dump_sqlalchemy()
    return db.dump_pg_dump()


def restore_database(db: DatabaseBackup, dump_bytes: bytes) -> None:
    if db._is_sqlite:
        db.restore_sqlalchemy(dump_bytes)
    else:
        db.restore_pg_restore(dump_bytes)


# ---------------------------------------------------------------------------
# Tenant-Discovery
# ---------------------------------------------------------------------------


def discover_tenants(db_url: str, fallback: list[str] | None = None) -> list[str]:
    """Ermittelt Tenant-DBs per ``pg_database``-Query oder greift auf die Config zurück."""
    try:
        engine = create_engine(db_url)
    except Exception:
        return list(fallback or [])
    try:
        if engine.dialect.name == "sqlite":
            return list(fallback or [])
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT datname FROM pg_database WHERE datname LIKE '%_planbar'")).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return list(fallback or [])
    finally:
        try:
            engine.dispose()
        except Exception:
            pass
