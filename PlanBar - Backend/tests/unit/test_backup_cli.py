"""Tests für ``app.backup.cli`` (Typer-CLI)."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from app.backup.cli import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def env_local(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_STORAGE_TYPE", "local")
    monkeypatch.setenv("BACKUP_LOCAL_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("BACKUP_DB_URL_PLANBAR", f"sqlite:///{tmp_path}/planbar.db")
    monkeypatch.setenv("BACKUP_LOCK_TTL_SECONDS", "60")
    monkeypatch.setenv("BACKUP_INCLUDE_MIGRATIONS", "false")


def _make_orch_factory(monkeypatch, providers=None):
    """Uebersteht die Orchestrator-Fabrik mit fixen Providern."""
    from app.backup.orchestrator import Orchestrator

    def factory(config, storage, **kwargs):
        prov = providers or {
            "planbar_db": lambda: b"PLANBAR_DUMP",
            "tito_db": lambda: b"TITO_DUMP",
            "uploads": lambda: b"UPLOADS",
            "config": lambda: b"CONFIG",
            "migrations": lambda: b"MIGRATIONS",
        }
        return Orchestrator(config, storage, component_providers=prov, **kwargs)

    monkeypatch.setattr("app.backup.cli.build_orchestrator", factory)


def test_cli_help(runner):
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "backup" in result.output.lower() or "Usage" in result.output


def test_cli_backup_all(runner, env_local, tmp_path, monkeypatch):
    _make_orch_factory(monkeypatch)
    result = runner.invoke(app, ["backup", "--tenant", "kunde1"])
    assert result.exit_code == 0, result.output
    # Backup wurde im Local-Storage erstellt
    backups_dir = tmp_path / "backups"
    manifests = list(backups_dir.rglob("manifest.json"))
    assert manifests


def test_cli_backup_single_component(runner, env_local, tmp_path, monkeypatch):
    _make_orch_factory(monkeypatch)
    result = runner.invoke(app, ["backup", "--tenant", "k1", "--component", "planbar_db"])
    assert result.exit_code == 0, result.output
    backups_dir = tmp_path / "backups"
    planbar_dumps = list(backups_dir.rglob("planbar_db.dump"))
    assert planbar_dumps


def test_cli_backup_single_tenant(runner, env_local, tmp_path, monkeypatch):
    _make_orch_factory(monkeypatch)
    result = runner.invoke(app, ["backup", "--tenant", "kunde42"])
    assert result.exit_code == 0, result.output
    backups_dir = tmp_path / "backups"
    found = [p.relative_to(backups_dir).parts[0] for p in backups_dir.rglob("manifest.json")]
    assert "kunde42" in found


def test_cli_backup_json_output(runner, env_local, monkeypatch):
    _make_orch_factory(monkeypatch)
    result = runner.invoke(app, ["backup", "--tenant", "k1", "--format", "json"])
    assert result.exit_code == 0, result.output
    # Output muss als JSON parsebar sein
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert payload["tenant"] == "k1"


def test_cli_backup_dry_run(runner, env_local, tmp_path, monkeypatch):
    _make_orch_factory(monkeypatch)
    result = runner.invoke(app, ["backup", "--tenant", "k1", "--dry-run"])
    assert result.exit_code == 0, result.output
    backups_dir = tmp_path / "backups"
    # Dry-Run -> keine Dateien geschrieben (aber Verzeichnis existiert)
    assert list(backups_dir.rglob("manifest.json")) == []


def test_cli_restore(runner, env_local, tmp_path, monkeypatch):
    _make_orch_factory(monkeypatch)
    # Backup erzeugen
    result = runner.invoke(app, ["backup", "--tenant", "k1"])
    assert result.exit_code == 0
    backups_dir = tmp_path / "backups"
    manifest_path = next(backups_dir.rglob("manifest.json"))
    manifest_key = str(manifest_path.relative_to(backups_dir))

    # Restore-Methoden mocken, da _providers keine echten Dump-Bytes liefert
    from app.backup.orchestrator import Orchestrator

    orig_init = Orchestrator.__init__

    def patched_init(self, config, storage, **kwargs):
        orig_init(self, config, storage, **kwargs)
        self._restore_db_component = lambda *a, **k: None
        self._restore_files_component = lambda *a, **k: None
        self._restore_migrations_component = lambda *a, **k: None

    monkeypatch.setattr(Orchestrator, "__init__", patched_init)
    result = runner.invoke(app, ["restore", manifest_key])
    assert result.exit_code == 0, result.output


def test_cli_list(runner, env_local, tmp_path, monkeypatch):
    _make_orch_factory(monkeypatch)
    runner.invoke(app, ["backup", "--tenant", "k1"])
    result = runner.invoke(app, ["list", "--tenant", "k1"])
    assert result.exit_code == 0, result.output
    assert "k1" in result.output


def test_cli_list_json(runner, env_local, monkeypatch):
    _make_orch_factory(monkeypatch)
    runner.invoke(app, ["backup", "--tenant", "k1"])
    result = runner.invoke(app, ["list", "--tenant", "k1", "--format", "json"])
    assert result.exit_code == 0, result.output
    lines = [
        line
        for line in result.output.strip().splitlines()
        if line.strip().startswith("[") or line.strip().startswith("{")
    ]
    assert lines
    payload = json.loads(lines[0])
    assert isinstance(payload, list)
    assert payload  # at least one


def test_cli_backup_locked_exits_2(runner, env_local, monkeypatch):
    # Acquire lock on the same storage the CLI will use via build_orchestrator-Patch
    from app.backup.orchestrator import Orchestrator

    def factory(config, _storage, **kwargs):
        # Force lock failure: pre-acquire lock on the SAME storage instance
        _storage.acquire_lock("backup", ttl_seconds=999)
        prov = {
            "planbar_db": lambda: b"X",
        }
        return Orchestrator(config, _storage, component_providers=prov, **kwargs)

    monkeypatch.setattr("app.backup.cli.build_orchestrator", factory)
    result = runner.invoke(app, ["backup", "--tenant", "k1"])
    assert result.exit_code == 2
