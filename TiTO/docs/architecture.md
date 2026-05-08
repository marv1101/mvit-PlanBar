# TiTO Architektur

TiTO ist als Queue-basierter Worker für Schichtplanung ausgelegt. Die Architektur besteht aus folgenden Teilen:

- `src/tito/worker.py`: Hauptschleife zum Lesen, Verarbeiten und Speichern von Jobs.
- `src/tito/db.py`: Schnittstelle zur PostgreSQL-Queue und zur Statusverwaltung.
- `src/tito/schema.py`: Pydantic-basierte Validierung für eingehende Jobpayloads mit Typsicherheit.
- `src/tito/solver.py`: Übersetzung in ein OR-Tools-Modell und Solver-Ausführung.
- `src/tito/api.py`: Flask-API für Health-Checks und Monitoring.
- `src/tito/auth.py`: Platzhalter für Authentifizierung und Autorisierung.
- `src/tito/monitoring.py`: Erfassung von Metriken wie Jobdauer und Fehlerquote.

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
