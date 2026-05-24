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
