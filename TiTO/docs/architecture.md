# TiTO Architektur

TiTO ist als Queue-basierter Worker für Schichtplanung ausgelegt. Die Architektur besteht aus folgenden Teilen:

- `src/tito/worker.py`: Hauptschleife zum Lesen, Verarbeiten und Speichern von Jobs.
- `src/tito/db.py`: Schnittstelle zur PostgreSQL-Queue und zur Statusverwaltung.
- `src/tito/schema.py`: Pydantic-basierte Validierung für eingehende Jobpayloads mit Typsicherheit.
- `src/tito/solver.py`: Übersetzung in ein OR-Tools-Modell und Solver-Ausführung.
- `src/tito/api.py`: Flask-API für Health-Checks und Monitoring.
- `src/tito/auth.py`: Authentifizierung (API-Token / JWT) und autorisierung (Rollen-Modell, Tenant-Mapping).
- `src/tito/monitoring.py`: Erfassung von Metriken wie Jobdauer und Fehlerquote.
- `src/tito/config.py`: Umgebungsvariablen und Token-Konfiguration.

## Tenant-Isolation

TiTO implementiert eine logische Mandantentrennung auf Code-Ebene (Defense-in-Depth), die sowohl im Database-per-Tenant-Betrieb (physische Isolation) als auch im Shared-Instance-Betrieb (eine TiTO-Instanz, mehrere Mandanten) sicher ist.

### Mechanismen

1. **Schema-Validierung beim Enqueue** (`api.py`): `POST /jobs` validiert das Payload gegen das Pydantic-Schema. `metadata.tenantId` (int ≥1) ist Pflicht. Ungültige Jobs werden mit `400` abgelehnt und erreichen nie die Queue oder den Worker.

2. **IDOR-Schutz** (`api.py`): Mandanten-scoped Tokens (via `API_TOKEN_TENANTS` oder JWT `tenant_id`) dürfen nur für ihren eigenen Tenant einreichen. Ein Mismatch zwischen Token-Tenant und Payload-Tenant liefert `403`.

3. **Tenant-scoped Lesezugriffe** (`api.py`, `db.py`): `/jobs`, `/jobs/{id}`, `/dlq`, `/callbacks/pending` filtern Ergebnisse nach dem authentifizierten Tenant. Cross-Tenant-Abfragen liefern `404` bzw. leere Listen.

4. **Mandanten-isolierte Metrics** (`monitoring.py`, `db.py`): `/metrics`, `/metrics/robustness`, `/metrics/prometheus` aggregieren nur Jobs des authentifizierten Tenants. Worker-Metriken sind nur für Admins ohne Tenant-Mapping sichtbar.

5. **Mandanten-scoped Idempotenz** (`db.py`): Composite-Unique-Index `(tenant_id, idempotency_key)` — derselbe Key darf pro Tenant unabhängig existieren. `tenant_id` ist `NOT NULL` in der `job_queue`-Tabelle.

6. **Typkonsistenz** (`schema.py`, `auth.py`, `db.py`): `tenant_id` wird überall als `str` normalisiert (DB-Spalte ist `TEXT`), um Typ-Mismatch-bedingte Filterfehler zu vermeiden. Die Helper-Funktion `extract_tenant_id()` akzeptiert sowohl `tenantId` (camelCase, schema-konform) als auch `tenant_id` (snake_case, vom Backend gesendet).

### Rollen-Modell (`auth.py`)

| Rolle | Erlaubte Endpunkte | Tenant-Kontext |
|-------|-------------------|----------------|
| `admin` | Alle | Ja (aus `API_TOKEN_TENANTS` oder JWT) |
| `worker` | `/workers/*` | Kein (Worker verarbeitet alle Jobs) |
| `metrics` | `/metrics` | Ja |
| `jobs` | `/jobs` | Ja |

### Umgebungsvariablen

| Variable | Beschreibung |
|----------|-------------|
| `API_TOKEN` / `API_TOKENS` | Kommaseparierte API-Tokens (Default-Rolle: `admin`) |
| `API_TOKEN_ROLES` | Mapping `token=role,token=role` |
| `API_TOKEN_TENANTS` | Mapping `token=tenant_id` für mandanten-scoped Tokens |
| `WORKER_API_TOKEN` | Dediziertes Worker-Token (Rolle `worker`) |
| `JWT_SECRET` | JWT-Signierschlüssel |
| `JWT_ALGORITHMS` | Erlaubte JWT-Algorithmen (Default: `HS256`) |

## Datenfluss

1. Job wird in PostgreSQL-Queue eingereiht.
2. Worker lädt Job, validiert JSON mit Pydantic und markiert ihn als `processing`.
3. Payload wird in ein Optimierungsmodell transformiert.
4. OR-Tools löst den Planungsfall.
5. Ergebnis und Metriken werden zurück in die Result-Queue geschrieben.

## Schema-Validierung mit Pydantic

TiTO verwendet **Pydantic** für die Validierung und Typisierung von JSON-Daten. Dies bietet folgende Vorteile:

- **Typsicherheit**: Alle Datenmodelle haben definierte Typen
- **Automatische Validierung**: Pydantic prüft Datentypen, Werte und Referenzen
- **Dokumentation**: Modelle dielen als automatische Dokumentation
- **IDE-Unterstützung**: Bessere Autovervollständigung und Type Hints

### Haupt-Modelle

- `JobPayload`: Haupt-Modell für eingehende Jobs
- `Metadata`: Job-Metadaten (ID, Tenant, Priorität)
- `Config`: Konfiguration für den Planungszeitraum
- `ShiftTemplate`: Schicht-Definitionen
- `Requirement`: Schicht-Anforderungen
- `Employee`: Mitarbeiter-Daten
- `Wish`: Mitarbeiter-Wünsche
- `JobResult`: Ergebnis-Modell für Ausgaben

### Validierungs-Features

- **Date-Format**: YYYY-MM-DD wird automatisch geprüft
- **Time-Format**: HH:MM wird automatisch geprüft
- **Referenzen**: Shift- und Employee-IDs werden auf Existenz geprüft
- **Range-Validierung**: Zahlenwerte werden auf gültige Bereiche geprüft
- **Forbidden Fields**: Unbekannte Felder werden abgelehnt (strict mode)

### Backward Compatibility

Die Funktion `validate_job_payload()` gibt ein `JobPayload`-Objekt zurück und kann weiterhin mit `model_dump()` in ein Dict umgewandelt werden, um die Kompatibilität mit bestehendem Code zu gewährleisten.
