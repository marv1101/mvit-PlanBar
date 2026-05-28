# PlanBar Backend

Backend für PlanBar mit FastAPI, PostgreSQL und TiTO-Integration.

## Setup

1. Erstelle ein virtuelles Environment im Backend-Ordner:
   - `python3 -m venv .venv`
2. Aktiviere das Environment:
   - `source .venv/bin/activate`
3. Installiere Abhängigkeiten:
   - `pip install -r requirements.txt`
4. Kopiere `.env.example` nach `.env` und passe die Werte an.
5. Starte den Server lokal:
   - `PYTHONPATH=src uvicorn app.main:app --reload`

## Datenbank & Migrationen

- Die Anwendung verwendet `DATABASE_URL` aus der `.env`.
- Beim Start werden Tabellen automatisch erstellt.
- Alternativ kannst du Alembic verwenden:
  - `alembic upgrade head`
  - `alembic revision --autogenerate -m "describe changes"`

## TiTO-Integration und Callbacks

### Konfiguration

Die TiTO-Integration erfordert die folgenden Umgebungsvariablen:

- `TITO_API_URL` – Die URL des TiTO-Diensts (Standard: `http://localhost:5001`)
- `BACKEND_CALLBACK_URL` – Die URL des Backends für TiTO-Callbacks (Standard: `http://localhost:8000`)
- `TITO_API_KEY` – Optionaler API-Schlüssel für TiTO (falls erforderlich)

### Callback-Flow

1. **Job-Submission**: Wenn eine Schedule an TiTO übermittelt wird, wird die `BACKEND_CALLBACK_URL` im Metadaten-Block enthalten.
2. **Job-Verarbeitung**: TiTO verarbeitet den Job und speichert die Metadaten.
3. **Callback**: Nach Abschluss sendet TiTO ein POST-Request an `{BACKEND_CALLBACK_URL}/api/v1/callbacks/tito` mit dem Ergebnis.
4. **Verarbeitung**: Das Backend aktualisiert die Schedule mit den Ergebnissen und erstellt neue Shiftplan-Einträge.

### Endpoint

- `POST /api/v1/callbacks/tito` – TiTO Callback-Empfang (für interne Kommunikation)

## Verfügbare Endpunkte

- `POST /api/v1/users` – Benutzer registrieren
- `POST /api/v1/users/login` – Login
- `POST /api/v1/users/refresh-token` – Access-/Refresh-Token erneuern
- `GET /api/v1/users/me` – Profil des angemeldeten Benutzers
- `GET /api/v1/users` – Benutzerliste (authentifiziert)
- `GET /api/v1/users/{user_id}` – Benutzer abrufen
- `PUT /api/v1/users/{user_id}` – Benutzer aktualisieren
- `DELETE /api/v1/users/{user_id}` – Benutzer löschen

## Test

- `pytest`

## Hinweise

- Die Struktur im `docs/` enthält das Implementierungsplan und Architekturübersicht.
- Aktuell wird ein Benutzerverwaltungskern mit JWT-Authentifizierung und SQLAlchemy-Persistenz aufgebaut.
