# TiTO Architektur

TiTO ist als Queue-basierter Worker für Schichtplanung ausgelegt. Die Architektur besteht aus folgenden Teilen:

- `src/tito/worker.py`: Hauptschleife zum Lesen, Verarbeiten und Speichern von Jobs.
- `src/tito/db.py`: Schnittstelle zur PostgreSQL-Queue und zur Statusverwaltung.
- `src/tito/schema.py`: JSON-Schema-Validierung für eingehende Jobpayloads.
- `src/tito/solver.py`: Übersetzung in ein OR-Tools-Modell und Solver-Ausführung.
- `src/tito/api.py`: Flask-API für Health-Checks und Monitoring.
- `src/tito/auth.py`: Platzhalter für Authentifizierung und Autorisierung.
- `src/tito/monitoring.py`: Erfassung von Metriken wie Jobdauer und Fehlerquote.

## Datenfluss

1. Job wird in PostgreSQL-Queue eingereiht.
2. Worker lädt Job, validiert JSON und markiert ihn als `processing`.
3. Payload wird in ein Optimierungsmodell transformiert.
4. OR-Tools löst den Planungsfall.
5. Ergebnis und Metriken werden zurück in die Result-Queue geschrieben.
