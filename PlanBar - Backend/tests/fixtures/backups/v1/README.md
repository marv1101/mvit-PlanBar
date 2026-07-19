# Fixture v1 – Manifest-Version 1.0

Dieser Fixture repräsentiert ein Backup aus der ersten Version des
modularen Python-Backups (Manifest v1.0). Die Datei `planbar_db.dump`
ist ein plaintext Dummy, das nur den Header des SQLite-Fallback-Formats
enthält – Restore-Tests nutzen den SQLAlchemy-Fallback, um den Dump zu
parsen.

Erzeugt mit: `app.backup` v0.1.0 gegen eine SQLite-Dev-DB.