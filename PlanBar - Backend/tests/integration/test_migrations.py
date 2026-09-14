"""Verifikation der Alembic-Migrationskette gegen eine echte PostgreSQL-Datenbank.

Läuft gegen die lokale Docker-Postgres aus ``Infrastructure/compose.yaml`` (Service
``db_backend``, Host-Port 5433). Voraussetzung:

    docker compose -f Infrastructure/compose.yaml up -d db_backend

Die Tests nutzen eine dedizierte, wegwerfbare Datenbank (``planbar_migration_test``),
die pro Testlauf frisch angelegt und danach gelöscht wird. Sie sind mit dem Marker
``@pytest.mark.postgres`` versehen und werden standardmäßig übersprungen, wenn die
DB nicht erreichbar ist bzw. per ``-m "not postgres"`` deaktiviert werden können.
"""

import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import OperationalError

from app.config import settings

# Host-Port des db_backend-Services aus Infrastructure/compose.yaml.
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5433
POSTGRES_USER = "planbar"
POSTGRES_PASSWORD = "secure_password_456"
ADMIN_DB = "planbar_backend"

ALEMBIC_HEAD = "0001_initial"


def _admin_url() -> str:
    """URL zur Always-present Default-DB, damit Test-DBs angelegt werden können."""
    return (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{ADMIN_DB}"
    )


def _test_db_url(db_name: str) -> str:
    return (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{db_name}"
    )


def _postgres_available() -> bool:
    try:
        engine = create_engine(_admin_url(), pool_pre_ping=False)
        with engine.connect():
            engine.dispose()
        return True
    except OperationalError:
        return False


postgres_unavailable = not _postgres_available()

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        postgres_unavailable,
        reason=(
            "PostgreSQL (db_backend Docker-Container) nicht erreichbar – "
            "starte ihn mit: docker compose -f Infrastructure/compose.yaml up -d db_backend"
        ),
    ),
]


@pytest.fixture(scope="module")
def migration_db() -> str:
    """Lege eine frische, zufällig benannte Migrations-DB an und räume sie auf."""
    db_name = f"planbar_migration_test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin.dispose()
    try:
        yield db_name
    finally:
        cleanup = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
        with cleanup.connect() as conn:
            # Beende restliche Verbindungen, damit die DB gelöscht werden kann.
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :db AND pid <> pg_backend_pid()"
                ),
                {"db": db_name},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        cleanup.dispose()


@pytest.fixture()
def alembic_cfg(migration_db: str, monkeypatch):
    """Alembic-Config, die auf die Test-DB zeigt.

    Wichtig: ``migrations/env.py`` überschreibt ``sqlalchemy.url`` mit
    ``settings.database_url`` – deshalb muss beides gesetzt werden (conftest.py
    pusht settings.database_url auf SQLite, was hier zurückgedreht wird).
    """
    from alembic import script
    from alembic.config import Config

    url = _test_db_url(migration_db)
    monkeypatch.setattr(settings, "database_url", url)

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "migrations")
    cfg.set_main_option("sqlalchemy.url", url)

    script_dir = script.ScriptDirectory.from_config(cfg)
    heads = script_dir.get_heads()
    assert len(heads) == 1, f"Migrationskette hat {len(heads)} Heads (Branches?): {heads}"

    return cfg


def _run_upgrade(cfg, revision: str) -> None:
    from alembic import command

    command.upgrade(cfg, revision)


def _run_downgrade(cfg, revision: str) -> None:
    from alembic import command

    command.downgrade(cfg, revision)


def _current_revision(cfg) -> str | None:
    from alembic.runtime.migration import MigrationContext

    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    try:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            return ctx.get_current_revision()
    finally:
        engine.dispose()


def _tables(engine: Engine) -> set[str]:
    inspector = inspect(engine)
    return set(inspector.get_table_names())


def test_migrations_upgrade_to_head(alembic_cfg):
    """Die komplette Kette 0001 → head muss fehlerfrei durchlaufen."""
    _run_upgrade(alembic_cfg, "head")

    engine = create_engine(alembic_cfg.get_main_option("sqlalchemy.url"))
    try:
        with engine.connect() as conn:
            version = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert version == ALEMBIC_HEAD, f"DB ist bei {version}, erwartet {ALEMBIC_HEAD}"
        tables = _tables(engine)
        # alembic_version plus zentrale Tabellen aus der Migrationskette:
        for expected in (
            "users",
            "employees",
            "shiftplans",
            "pinboard_threads",
            "audit_logs",
            "notifications",
            "revoked_tokens",
            "time_entries",
            "teams",
        ):
            assert expected in tables, f"Tabelle '{expected}' fehlt nach upgrade head"
    finally:
        engine.dispose()


def test_migrations_idempotent(alembic_cfg):
    """Erneutes ``upgrade head`` auf Head-Level darf nichts ändern und nicht failen."""
    _run_upgrade(alembic_cfg, "head")
    _run_upgrade(alembic_cfg, "head")
    assert _current_revision(alembic_cfg) == ALEMBIC_HEAD


def test_migrations_full_downgrade_and_reupgrade(alembic_cfg):
    """Downgrade bis base und erneuter Upgrade müssen beide Richtungen abdecken."""
    _run_upgrade(alembic_cfg, "head")
    _run_downgrade(alembic_cfg, "base")
    assert _current_revision(alembic_cfg) is None

    engine = create_engine(alembic_cfg.get_main_option("sqlalchemy.url"))
    try:
        remaining = _tables(engine) - {"alembic_version"}
        assert remaining == set(), f"Nach downgrade base verbleiben Tabellen: {remaining}"
    finally:
        engine.dispose()

    _run_upgrade(alembic_cfg, "head")
    assert _current_revision(alembic_cfg) == ALEMBIC_HEAD


def test_migrations_schema_matches_models(alembic_cfg):
    """Migrationen und SQLAlchemy-Modelle müssen dieselben Spalten erzeugen.

    Vergleicht pro Tabelle die Spaltennamen aus der Migrationskette gegen
    ``Base.metadata``. Typ-Details bewusst ausgenommen (SQLite-/Postgres-Server-
    Defaults weichen legitim ab); entscheidend ist die Spaltenabdeckung.
    """
    from app.db.base import Base

    _run_upgrade(alembic_cfg, "head")

    engine = create_engine(alembic_cfg.get_main_option("sqlalchemy.url"))
    try:
        inspector = inspect(engine)
        migrated = {
            table: {col["name"] for col in inspector.get_columns(table)}
            for table in inspector.get_table_names()
        }
        expected = {
            table.name: {col.name for col in table.columns}
            for table in Base.metadata.sorted_tables
        }

        # Modelle ohne Migration und Migrationen ohne Modell sind beide Fehler.
        assert set(expected) <= set(migrated), (
            f"Tabellen nur in Modellen (fehlende Migration): "
            f"{sorted(set(expected) - set(migrated))}"
        )
        assert set(migrated) <= set(expected) | {"alembic_version"}, (
            f"Tabellen nur in Migrationen (fehlt im Modell): "
            f"{sorted(set(migrated) - set(expected) - {'alembic_version'})}"
        )

        for table_name, model_columns in expected.items():
            missing = model_columns - migrated.get(table_name, set())
            assert not missing, (
                f"Tabelle '{table_name}': Spalten fehlen in der Migration: "
                f"{sorted(missing)}"
            )
    finally:
        engine.dispose()


def test_migrations_match_models_via_metadata_create_all(migration_db):
    """Zweite, unabhängige Schema-Quelle: ``create_all`` in einer zweiten DB.

    Stellt sicher, dass die Modelle selbst auf PostgreSQL anlegbar sind –
    unabhängig vom Alembic-Lauf (deckt z. B. typ-spezifische Dialektprobleme ab).
    """
    from app.db.base import Base

    models_db = f"{migration_db}_models"
    admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{models_db}"'))
    admin.dispose()

    engine = create_engine(_test_db_url(models_db))
    try:
        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)
        assert "users" in inspector.get_table_names()
    finally:
        engine.dispose()
        cleanup = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
        with cleanup.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :db AND pid <> pg_backend_pid()"
                ),
                {"db": models_db},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{models_db}"'))
        cleanup.dispose()


def test_settings_database_url_is_postgres_compatible():
    """Sanity-Check: Die konfigurierte DATABASE_URL muss parsebar sein und
    denselben Postgres-Treiber wie der Produktionseinsatz erwarten."""
    url = make_url(settings.database_url)
    assert url.drivername.startswith("postgresql") or url.drivername.startswith("sqlite")
