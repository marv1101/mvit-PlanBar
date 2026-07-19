# Fixture v2 – Manifest-Version 2.0

Manifest-Version 2.0 erweitert v1.0 um `encryption` und `compression`
pro Komponente. Dieser Fixture repräsentiert ein Backup, das nach der
Migration von v1.0 -> v2.0 entstanden ist.

Die `.dump`-Dateien sind SQLite-Fallback-Dumps (kein pg_dump), damit der
Restore in der CI ohne PostgreSQL-Client funktioniert.

Erzeugt mit: `app.backup` v0.2.0 gegen eine SQLite-Dev-DB.