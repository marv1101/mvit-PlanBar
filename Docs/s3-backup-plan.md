# S3-kompatibles modulares Backup-Backend

## 1. Status Quo

Aktuell existiert nur ein Shell-Skript (`Infrastructure/scripts/backup.sh`), das per `pg_dump`
PostgreSQL-Dumps aller Tenant-DBs erzeugt und lokal in `/opt/planbar/backups/` ablegt.
Ein Restore-Skript (`restore.sh`) stellt einzelne Tenant-DBs wieder her.

**Lücken:**
- Kein Backup von Datei-Uploads (`uploads/pinboard/`)
- Kein Backup der Anwendungskonfiguration
- Kein S3/Object-Store-Support (nur als rclone-Kommentar erwähnt)
- Keine Metadaten / kein Manifest – Dumps sind nur an Dateinamen erkennbar
- Keine Schema-Versionierung – bei DB-Migrationen ist unklar, zu welcher Schema-Version ein Dump gehört

## 2. Zielsetzung

1. **S3-kompatibler Object-Store-Support** – Backup direkt in S3/MinIO/Backblaze B2
2. **Modularität** – Jede Komponente (Storage, DB, Dateien, Metadaten) austauschbar
3. **Rückwärtskompatibilität** – Bestehende Shell-Skripte laufen weiter; neue Python-CLI kann parallel betrieben werden
4. **Schema-Evolution** – Backups enthalten Schema-Version und Migrations-History; Restore funktioniert auch nach Schema-Änderungen
5. **TDD** – Tests werden vor der Implementierung definiert

## 3. Architektur

### 3.0 Laufzeitumgebung

Das Backup-Modul läuft **immer innerhalb des `planbar_backend`-Containers**, nicht auf dem Host.
Das Container-Image wird um `pg_dump`/`pg_restore` (aus `postgresql-client`) sowie `boto3`
erweitert. Dadurch entfällt die `docker exec`-Indirektion; das Modul verbindet sich direkt via
Docker-Netzwerk zur DB (`db_planbar`/`db_backend`).

```dockerfile
# Ergänzung zum bestehenden Dockerfile
RUN apt-get install -y --no-install-recommends postgresql-client-15
```

Für lokale Tests und SQLite-Dev-Umgebungen existiert ein SQLAlchemy-basierter Fallback,
der ohne `pg_dump` auskommt (siehe `database.py`).

### 3.1 Paketstruktur

Neues Python-Paket unter `PlanBar - Backend/src/app/backup/`:

```
src/app/backup/
├── __init__.py           # Public API-Export
├── config.py             # Pydantic Settings für Backup-Konfiguration
├── metadata.py           # Backup-Manifest (versioniert, selbstbeschreibend)
├── storage.py            # Storage-Interface + Local/S3-Implementierung
├── database.py           # DB-Dump/Restore (pg_dump/pg_restore)
├── files.py              # Datei-Archivierung
├── orchestrator.py       # orchestriert backup_all / restore_all
├── cli.py                # CLI-Einstiegspunkt (typer)
└── exceptions.py         # Domain-Exceptions
```

### 3.2 Storage-Interface (Strategy Pattern)

```python
class BackupStorage(ABC):
    def upload(self, key: str, data: bytes, metadata: dict | None = None) -> str: ...
    def download(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def head(self, key: str) -> BackupInfo: ...
    def list_backups(self, prefix: str, *, page_size: int = 100,
                     page_token: str | None = None) -> BackupListPage: ...
    def delete(self, key: str) -> None: ...
    def acquire_lock(self, lock_key: str, ttl_seconds: int = 300) -> bool: ...
    def release_lock(self, lock_key: str) -> None: ...

@dataclass
class BackupListPage:
    items: list[BackupInfo]
    next_page_token: str | None

@dataclass
class BackupInfo:
    key: str
    size_bytes: int
    last_modified: datetime
    metadata: dict
    checksum_sha256: str | None
```

Paginierung ist zwingend, weil bei jahrelangen Backup-Runs tausende Objekte auflaufen können.
`acquire_lock`/`release_lock` verhindern parallele Backup-Läufe (Distributed Lock via S3
Conditional Put oder lokale Lock-Datei).

Implementierungen:
- `LocalStorage` – für Tests und lokale Entwicklung
- `S3Storage` – für S3-kompatible Object Stores (via boto3)

### 3.3 Backup-Manifest (JSON, versioniert)

Das Manifest ist die zentrale Datenstruktur: es beschreibt, welche Komponenten in
einem Backup-Lauf gesichert wurden, zu welcher Schema-Version und mit welchen Prüfsummen.
Es wird selbst als JSON-Datei im Backup abgelegt (Key: `<prefix>/manifest.json`).

**Regel für Migrations-Dateien:** Alembic-Migrationsskripte werden im Codebase-Repo
niemals gelöscht, sondern nur *überschrieben* (squashed) oder ergänzt. Dadurch ist
garantiert, dass bei einem Restore eines alten Dumps die passenden Migrationsdateien
noch existieren.

```json
{
  "manifest_version": "1.0",
  "created_at": "2026-07-14T03:00:00Z",
  "tool_version": "0.1.0",
  "tenant": "kunde1",
  "verified": true,
  "components": {
    "planbar_db": {
      "type": "postgres_dump",
      "format": "custom",
      "alembic_version": "0010",
      "migration_history": ["0001", "0002", "0003", "0004", "0005",
                            "0006", "0007", "0008", "0009", "0010"],
      "key": "kunde1/20260714-030000/planbar_db.dump",
      "size_bytes": 245821,
      "checksum_sha256": "abc123..."
    },
    "tito_db": {
      "type": "postgres_dump",
      "format": "custom",
      "schema_version": "1.0",
      "key": "kunde1/20260714-030000/tito_db.dump",
      "size_bytes": 18932,
      "checksum_sha256": "def456..."
    },
    "uploads": {
      "type": "tar_gz",
      "key": "kunde1/20260714-030000/uploads.tar.gz",
      "size_bytes": 1048576,
      "checksum_sha256": "789abc..."
    },
    "config": {
      "type": "env_dir",
      "key": "kunde1/20260714-030000/config.tar.gz",
      "checksum_sha256": "xyz..."
    },
    "migrations": {
      "type": "directory_archive",
      "key": "kunde1/20260714-030000/migrations.tar.gz",
      "checksum_sha256": "..."
    }
  }
}
```

**Anmerkung:** Checksums sind direkt in jeder Komponente gespeichert (nicht nur im
Top-Level-Objekt) – so kann ein beschädigter Upload isoliert identifiziert werden.
Das `verified`-Feld wird nach Upload auf `true` gesetzt, nachdem alle Objekte
heruntergeladen und gegen ihre Checksum geprüft wurden.

### 3.4 Schema-Evolution & Manifest-Migration

| Mechanismus | Beschreibung |
|-------------|-------------|
| `manifest_version` | Wird hochgezählt bei Format-Änderungen des Manifests selbst |
| `alembic_version` | Aktuelle Alembic-Version der gedumpten DB |
| `migration_history` | Komplette Liste aller Migrationen zum Backup-Zeitpunkt |
| Mitgelieferte Migrations-Dateien | `migrations/versions/` wird als `.tar.gz` beigelegt |
| Restore-Strategie | Nach pg_restore: `alembic upgrade head` nur bei Versions-Differenz |

**Manifest-Migration zwischen Versionen:**

Jede `manifest_version`änderung braucht einen Migrator. Beim Laden eines Manifests
läuft die `from_dict()`-Factory durch folgende Dispatch-Tabelle:

```python
MANIFEST_MIGRATORS: dict[str, Callable[[dict], dict]] = {
    "0.9": _migrate_v09_to_v10,
    "1.0": _migrate_v10_to_v20,
}

def Manifest_from_dict(raw: dict) -> Manifest:
    version = raw.get("manifest_version", "0.9")
    while version in MANIFEST_MIGRATORS:
        raw = MANIFEST_MIGRATORS[version](raw)
        version = raw.get("manifest_version", "1.0")
    return Manifest(**raw)
```

Jeder Migrator ist eine pure function: `dict -> dict`, die das Eingabe-Dict in das Format
der nächsthöheren Version transformiert. So bleiben **Jahre alte Backups lesbar**, indem
das alte JSON beim Laden in die aktuellste Version konvertiert wird.

**Multi-Tenant-Discovery:**

Das Backup-Modul entdeckt Tenants entweder automatisch oder per expliziter Liste:

```python
def discover_tenants(db_connection_string: str) -> list[str]:
    """Listet alle Tenant-DBs per SQL-Query auf."""
    # SELECT datname FROM pg_database WHERE datname LIKE '%_planbar'
```

Config-Option `BACKUP_TENANTS` (Komma-getrennt) dient als Fallback, wenn kein SQL-Zugriff möglich ist
oder nur bestimmte Tenants gesichert werden sollen. Ist die Liste leer, wird automatisch discovered.

### 3.5 Rückwärtskompatibilität & Locking

- Shell-Skripte bleiben unverändert – neues Python-Modul läuft parallel
- Python-CLI kann als Drop-in-Replacement für `backup.sh` konfiguriert werden
- Restore erkennt sowohl alte `.dump`-Dateien ohne Manifest als auch neue S3-Backups mit Manifest
- Fehlt ein Manifest, werden Default-Metadaten angenommen
- **Locking**: `orchestrator.backup_all()` akquiriert ein Lock (via `storage.acquire_lock()`).
  Default-TTL: 5 Minuten, wird im laufenden Backup regelmäßig verlängert. Wird das Lock nicht
  akquiriert, bricht das Backup mit Exit-Code 2 ab (nicht 1 – unterscheidbar von echten Fehlern).

### 3.6 Restore-Reihenfolge

Der Orchestrator stellt in fester Reihenfolge wieder her:

1. **Config** – damit DB-Credentials und Pfade vor dem DB-Restore gültig sind
2. **Migrations** – Migrations-Dateien werden vor dem Restore ausgepackt, damit Alembic sie kennt
3. **DBs** (planbar_db → tito_db) – pg_restore, dann ggf. `alembic upgrade head`
4. **Uploads** – Dateiarchiv entpacken

Nach jedem Schritt wird validiert, dass die Komponente erfolgreich wiederhergestellt wurde,
bevor der nächste Schritt beginnt. Ein `restore_all()`-Aufruf kann auch eine einzelne
Komponente restaurieren (`--component planbar_db`).

## 4. Tests (TDD)

### 4.0 Test-Fixtures für alte Backup-Formate

Damit auch in Jahren noch alte Backup-Formate lesbar bleiben, liegen unter
`tests/fixtures/backups/` eingefrorene Testdaten:

```
tests/fixtures/backups/
├── v1/
│   ├── manifest.json          # Manifest v1 (minimal, nur DB)
│   ├── planbar_db.dump        # SQLite-Dump zu Manifest v1 passend
│   └── README.md              # Beschreibung, wann/womit erzeugt
├── v2/
│   ├── manifest.json          # Manifest v2 (mit uploads, config)
│   └── ...
```

Die CI (`ci.yml`) prüft einen dedizierten Test, der *alle* Fixture-Versionen lädt
und als lesbar deklariert. So wird verhindert, dass zukünftige Code-Änderungen die
Kompatibilität zu alten Formaten brechen.

### 4.1 Storage-Layer (`tests/unit/test_backup_storage.py`)

| Test | Beschreibung |
|------|-------------|
| `test_local_storage_upload_download` | LocalStorage upload + download rundet korrekt |
| `test_local_storage_atomic_write` | LocalStorage schreibt erst nach tmp, dann rename (kein Halbzeug) |
| `test_local_storage_list_backups` | LocalStorage listet nach Prefix |
| `test_local_storage_list_page_two` | Paginierung: zweite Seite wird korrekt abgerufen |
| `test_local_storage_list_backups_pagination` | Letzte Seite hat `next_page_token = None` |
| `test_local_storage_delete` | LocalStorage löscht korrekt |
| `test_local_storage_exists` | `exists()` liefert True/False |
| `test_local_storage_head` | `head()` liefert Metadaten ohne Download |
| `test_local_storage_not_found` | Nicht existierender Key -> Exception |
| `test_local_storage_lock_acquire` | Lock wird akquiriert |
| `test_local_storage_lock_contention` | Zweiter Lauf bekommt kein Lock |
| `test_local_storage_lock_release` | Nach Release kann erneut gelockt werden |
| `test_local_storage_lock_ttl_expiry` | Nach TTL-Ablauf ist Lock wieder frei |
| `test_s3_storage_upload_download` | S3Storage via moto: upload + download |
| `test_s3_storage_list_backups` | S3 listet Objekte nach Prefix |
| `test_s3_storage_list_backups_pagination` | Paginierung über S3 Continuation Tokens |
| `test_s3_storage_delete` | S3 löscht Objekte |
| `test_s3_storage_metadata` | Benutzerdefinierte Metadaten werden gespeichert |
| `test_s3_storage_lock_acquire` | Conditional Put als Lock |
| `test_s3_storage_lock_contention` | 409 Conflict bei Concurrent Lock |
| `test_storage_interface_contract` | LocalStorage + S3Storage erfüllen gleichen Contract |
| `test_storage_factory` | Factory erzeugt korrekten Storage-Typ |

### 4.2 DB-Backup (`tests/unit/test_backup_database.py`)

| Test | Beschreibung |
|------|-------------|
| `test_get_alembic_current_version` | Aktuelle Alembic-Version aus der DB lesen |
| `test_get_alembic_migration_history` | Komplette Historie aus `alembic_version` |
| `test_dump_database_via_sqlalchemy` | Fallback-Dump: SQLAlchemy COPY-basierter Export (SQLite) |
| `test_dump_database_via_pg_dump` | pg_dump via Subprocess (gemockt) |
| `test_dump_database_failure` | Fehler bei DB-Connection |
| `test_restore_database_from_bytes` | pg_restore mit Dump-Bytes |
| `test_restore_database_sqlalchemy_fallback` | SQLAlchemy-basierter Restore (SQLite/Dev) |
| `test_discover_tenants_from_db` | Tenant-Liste via SQL-Query |
| `test_discover_tenants_from_config` | Explizite Tenant-Liste aus Config |
| `test_discover_tenants_empty_fallback` | Weder DB noch Config -> leer |
| `test_backup_schema_migrations` | Migrations-Skripte werden beigelegt |
| `test_restore_with_old_schema` | Alter Dump + Migration auf neue Version |

### 4.3 File-Backup (`tests/unit/test_backup_files.py`)

| Test | Beschreibung |
|------|-------------|
| `test_archive_uploads_directory` | tar.gz aus upload-Verzeichnis |
| `test_archive_empty_directory` | Leeres Verzeichnis -> leeres Archiv |
| `test_archive_preserves_structure` | Relative Pfade im Archiv |
| `test_extract_archive` | Extraktion stellt Struktur wieder her |
| `test_backup_with_ignored_patterns` | Ignorierte Files werden ausgelassen |

### 4.4 Metadaten/Manifest (`tests/unit/test_backup_metadata.py`)

| Test | Beschreibung |
|------|-------------|
| `test_manifest_create_minimal` | Manifest mit Pflichtfeldern |
| `test_manifest_create_full` | Manifest mit allen Komponenten |
| `test_manifest_serialize_deserialize` | JSON-Rundlauf |
| `test_manifest_validation` | Ungültige Manifests werden abgewiesen |
| `test_manifest_version_check` | Manifest-Version validieren |
| `test_manifest_backward_compat_v1` | Manifest v1 von Fixture wird noch geladen |
| `test_manifest_migration_v09_to_v10` | v0.9 Dict -> v1.0 Manifest (fehlende Felder ergänzt) |
| `test_manifest_migration_v10_to_v20` | v1.0 Dict -> v2.0 Manifest |
| `test_manifest_checksums_per_component` | Checksum pro Komponente (nicht nur Top-Level) |
| `test_manifest_verified_false_after_creation` | Neues Manifest hat `verified: false` |
| `test_manifest_verified_true_after_validation` | Nach Checksum-Prüfung: `verified: true` |
| `test_manifest_migration_chain_three_steps` | v0.9 -> v1.0 -> v2.0 in einem Durchlauf |

### 4.5 Schema-Evolution (`tests/unit/test_backup_schema_evolution.py`)

| Test | Beschreibung |
|------|-------------|
| `test_backup_includes_migration_files` | Migrationsverzeichnis im Backup |
| `test_restore_detects_schema_mismatch` | Abweichende Version wird erkannt |
| `test_restore_migrates_if_needed` | Automatische Migration nach Restore |
| `test_restore_skips_migration_if_matching` | Gleiche Version -> kein Lauf |
| `test_restore_old_schema_with_new_code` | Alter Dump + neue Codebase lesbar |
| `test_manifest_version_migration` | Manifest v0 -> v1 migrierbar |

### 4.6 Orchestrator (`tests/unit/test_backup_orchestrator.py`)

| Test | Beschreibung |
|------|-------------|
| `test_backup_all_components` | Kompletter Backup-Lauf |
| `test_backup_partial_failure` | Fehler in einer Komponente stoppt andere nicht |
| `test_backup_locks_before_start` | Lock wird akquiriert, bevor Komponenten starten |
| `test_backup_refuses_when_locked` | Exit-Code 2, wenn Lock nicht akquirierbar |
| `test_backup_releases_lock_after_completion` | Lock wird auch bei Fehler released |
| `test_backup_verify_after_upload` | Nach Upload: Download + Checksum-Prüfung |
| `test_backup_retention` | Alte Backups werden gelöscht |
| `test_backup_retention_min_age` | Mindestalter vor Löschung wird eingehalten |
| `test_restore_all_components` | Kompletter Restore aus Manifest |
| `test_restore_correct_order` | Config → Migrations → DB → Uploads |
| `test_restore_single_component` | Nur eine Komponente |
| `test_restore_dry_run` | Dry-Run ohne Änderungen |
| `test_restore_fails_if_component_missing` | Fehlende Komponente im Manifest -> Error |
| `test_backup_skip_if_not_configured` | Fehlende Komponenten überspringen |
| `test_backup_with_s3_target` | Backup in S3-Bucket |
| `test_restore_from_s3_source` | Restore aus S3-Bucket |
| `test_backup_without_manifest` | Legacy-Dump ohne Manifest -> Default-Metadaten |

### 4.7 Konfiguration (`tests/unit/test_backup_config.py`)

| Test | Beschreibung |
|------|-------------|
| `test_config_defaults` | Standardwerte korrekt |
| `test_config_env_override` | ENV überschreibt Defaults |
| `test_config_s3_endpoint_optional` | S3-Endpoint optional (für AWS S3) |
| `test_config_invalid_retention` | Negative Retention -> Fehler |
| `test_config_storage_type_selection` | `BACKUP_STORAGE_TYPE`-Auswahl |

### 4.8 CLI (`tests/unit/test_backup_cli.py`)

| Test | Beschreibung |
|------|-------------|
| `test_cli_backup_all` | `backup`-Kommando |
| `test_cli_backup_single_component` | `backup --component planbar_db` |
| `test_cli_backup_single_tenant` | `backup --tenant kunde1` |
| `test_cli_restore` | `restore <manifest-key>` |
| `test_cli_list` | `list` zeigt verfügbare Backups |
| `test_cli_list_json` | `list --format json` gibt JSON aus |
| `test_cli_backup_json_output` | `backup --format json` gibt Manifest als JSON |
| `test_cli_dry_run` | `--dry-run` |
| `test_cli_help` | `--help` |

### 4.9 Integration (`tests/integration/test_backup_flow.py`)

| Test | Beschreibung |
|------|-------------|
| `test_backup_restore_roundtrip_local` | Full roundtrip LocalStorage |
| `test_backup_restore_roundtrip_s3` | Full roundtrip S3 (moto) |
| `test_backup_verify_checksums_after_upload` | Nach Backup: Download + Prüfung |
| `test_backup_detects_corrupted_upload` | Manipulierter Upload -> verified bleibt false |
| `test_backup_idempotent` | Zwei Läufe -> unterschiedliche Dateien |
| `test_restore_overwrites_existing` | Restore überschreibt |
| `test_backup_with_sqlite_dump` | Dump + Restore + Daten-Integrität |
| `test_backwards_compat_with_shell_script` | Von `backup.sh` erzeugter Dump lesbar |
| `test_fixture_v1_manifest_loadable` | Fixture `tests/fixtures/backups/v1/manifest.json` noch lesbar |
| `test_fixture_v1_restore_simulation` | Mit Fixture v1: Manifest parsen + Komponenten auflisten |
| `test_backup_lock_prevents_concurrent_run` | Zwei Prozesse, einer bekommt kein Lock |
| `test_backup_retention_deletes_old_backups` | Nach 31 Tagen wird gelöscht (Mock-Zeit) |

## 5. Neue Abhängigkeiten

### 5.1 Python-Pakete

```toml
# pyproject.toml (Produktion)
boto3>=1.34.0
typer>=0.12.0

# testing extras
moto>=5.0.0
```

### 5.2 System-Pakete (Dockerfile)

```dockerfile
# Ergänzung zu PlanBar - Backend/Dockerfile
# postgresql-client stellt pg_dump/pg_restore bereit
RUN apt-get install -y --no-install-recommends postgresql-client-15
```

### 5.3 Aktualisierung beider Dependency-Dateien

Das Projekt führt Dependencies doppelt (`pyproject.toml` und `requirements.txt`).
Bei der Implementierung müssen **beide** Dateien aktualisiert werden, da der
Dockerfile `requirements.txt` für `pip install` nutzt.

## 6. Konfiguration (Umgebungsvariablen)

```
BACKUP_STORAGE_TYPE=local|s3
BACKUP_TENANTS=kunde1,kunde2            # explizit oder leer für Auto-Discovery
BACKUP_LOCAL_DIR=/opt/planbar/backups

BACKUP_S3_BUCKET=planbar-backups
BACKUP_S3_ENDPOINT=https://s3.example.com          # optional (für AWS S3 leer lassen)
BACKUP_S3_REGION=eu-central-1
BACKUP_S3_ACCESS_KEY_ID=...
BACKUP_S3_SECRET_ACCESS_KEY=...
BACKUP_S3_PATH_PREFIX=planbar/                      # optional

BACKUP_RETENTION_DAYS=30
BACKUP_VERIFY_UPLOAD=true              # Checksums nach Upload prüfen
BACKUP_LOCK_TTL_SECONDS=300           # TTL für Distributed Lock

BACKUP_DB_URL_PLANBAR=postgresql://planbar:xxx@db_planbar:5432
BACKUP_DB_URL_TITO=postgresql://tito:xxx@db_tito:5432
BACKUP_UPLOADS_DIR=./uploads/pinboard
BACKUP_CONFIG_DIR=./config
BACKUP_INCLUDE_MIGRATIONS=true
```

**Wichtig:** `BACKUP_DB_HOST`/`PORT`/`USER`/`PASSWORD` wurden durch vollständige
Connection-Strings (`BACKUP_DB_URL_PLANBAR`, `BACKUP_DB_URL_TITO`) ersetzt.
Das vermeidet Mapping-Fehler und ist konsistent mit der bestehenden `DATABASE_URL`-Konvention
der App.

## 7. Implementierungs-Reihenfolge

| Schritt | Package | Tests |
|---------|---------|-------|
| 1 | `exceptions.py`, `config.py` | `test_backup_config.py` |
| 2 | `metadata.py` (Manifest + Migration) | `test_backup_metadata.py` |
| 3 | `storage.py` (Interface + Local + S3 + Lock) | `test_backup_storage.py` |
| 4 | `database.py` (pg_dump + SQLAlchemy-Fallback + Discovery) | `test_backup_database.py` |
| 5 | `files.py` | `test_backup_files.py` |
| 6 | Fixtures anlegen | `tests/fixtures/backups/v1/` + `v2/` |
| 7 | `orchestrator.py` (backup_all / restore_all / verify / lock) | `test_backup_orchestrator.py` + `test_backup_schema_evolution.py` |
| 8 | `cli.py` (typer, `--format json`) | `test_backup_cli.py` |
| 9 | Integration | `tests/integration/test_backup_flow.py` |
| 10 | `__init__.py` (Public API) | – |

## 8. Abgrenzung (nicht enthalten)

- **Live-Restore im laufenden Betrieb** – Restore setzt gestoppte App voraus
- **Inkrementelle Backups** – zunächst nur Voll-Backups
- **Clientseitige Verschlüsselung** – Object-Store kann serverseitig verschlüsseln (SSE-S3/SSE-KMS)
- **FastAPI-Endpoint für Backup/Restore** – zunächst nur CLI; ein Admin-Endpoint kann später folgen
- **Monitoring/Prometheus-Export** – Logging ist enthalten; Metriken-Export folgt bei Bedarf
- **Integrations-Test gegen echtes S3/MinIO** – moto reicht für Unit/Integration; ein optionaler Test gegen eine Docker-MinIO-Instanz kann später ergänzt werden
- **Backup des TiTO-Worker-State** – TiTO ist zustandslos in der DB; Worker-Daten werden aus dem DB-Dump wiederhergestellt
