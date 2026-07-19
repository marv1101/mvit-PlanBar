"""Typer-CLI fuer das Backup-Modul.

Einstiegspunkt: ``planbar-backup`` (siehe pyproject.toml [project.scripts]).
"""

from __future__ import annotations

import json
from typing import Any

import typer

from app.backup.config import BackupConfig
from app.backup.exceptions import BackupError, BackupLockError
from app.backup.orchestrator import Orchestrator
from app.backup.storage import storage_factory

app = typer.Typer(help="S3-kompatibles Backup-Backend fuer PlanBar", add_completion=False)


# ---------------------------------------------------------------------------
# Factories (für Tests überschreibbar)
# ---------------------------------------------------------------------------


def build_storage(config: BackupConfig):
    return storage_factory(
        config.storage_type,
        local_dir=config.local_dir,
        s3_bucket=config.s3_bucket or "",
        s3_region=config.s3_region,
        s3_endpoint=config.s3_endpoint,
        s3_access_key_id=config.s3_access_key_id,
        s3_secret_access_key=config.s3_secret_access_key,
        s3_path_prefix=config.s3_path_prefix,
    )


def build_orchestrator(config: BackupConfig, storage, **kwargs) -> Orchestrator:
    return Orchestrator(config, storage, **kwargs)


def _format_output(payload: Any, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(payload, default=str)
    return str(payload)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def backup(
    tenant: str = typer.Option(..., "--tenant", "-t"),
    component: list[str] | None = typer.Option(None, "--component", "-c", help="Komponente(n) gezielt sichern"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    fmt: str = typer.Option("text", "--format", help="text | json"),
):
    """Erzeugt ein neues Backup fuer einen Tenant."""
    config = BackupConfig()
    storage = build_storage(config)
    orch = build_orchestrator(config, storage)
    try:
        manifest = orch.backup_all(
            tenant=tenant,
            components=component,
            dry_run=dry_run,
        )
    except BackupLockError:
        typer.echo("backup lock could not be acquired", err=True)
        raise typer.Exit(code=2)
    except BackupError as exc:
        typer.echo(f"backup failed: {exc}", err=True)
        raise typer.Exit(code=1)
    payload = manifest.to_dict()
    typer.echo(_format_output(payload, fmt))
    raise typer.Exit(code=0)


@app.command()
def restore(
    manifest_key: str = typer.Argument(..., help="Storage-Key des manifest.json"),
    component: list[str] | None = typer.Option(None, "--component", "-c"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    fmt: str = typer.Option("text", "--format"),
):
    """Stellt ein Backup aus einem Manifest wieder her."""
    config = BackupConfig()
    storage = build_storage(config)
    orch = build_orchestrator(config, storage)
    try:
        result = orch.restore_all(
            manifest_key=manifest_key,
            components=component,
            dry_run=dry_run,
        )
    except BackupError as exc:
        typer.echo(f"restore failed: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(_format_output(result, fmt))
    raise typer.Exit(code=0)


@app.command(name="list")
def list_backups(
    tenant: str | None = typer.Option(None, "--tenant", "-t"),
    fmt: str = typer.Option("text", "--format"),
    page_size: int = typer.Option(100, "--page-size"),
):
    """Listet verfuegbare Backups im Storage auf."""
    config = BackupConfig()
    storage = build_storage(config)
    prefix = f"{tenant}/" if tenant else ""
    token = None
    items = []
    while True:
        page = storage.list_backups(prefix=prefix, page_size=page_size, page_token=token)
        items.extend(page.items)
        if page.next_page_token is None:
            break
        token = page.next_page_token
    manifests = [i for i in items if i.key.endswith("/manifest.json")]
    if fmt == "json":
        payload = [{"key": i.key, "size_bytes": i.size_bytes, "last_modified": str(i.last_modified)} for i in manifests]
        typer.echo(json.dumps(payload, default=str))
    else:
        for i in manifests:
            typer.echo(f"{i.last_modified}\t{i.size_bytes}\t{i.key}")
    raise typer.Exit(code=0)


if __name__ == "__main__":  # pragma: no cover
    app()
