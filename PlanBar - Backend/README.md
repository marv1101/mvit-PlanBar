# PlanBar Backend

Backend für PlanBar mit FastAPI, PostgreSQL und TiTO-Integration.

## Setup

1. Erstelle ein virtuelles Environment im Backend-Ordner: `python3 -m venv .venv`
2. Aktiviere das Environment: `source .venv/bin/activate` (oder `.venv\Scripts\activate` auf Windows)
3. Installiere Abhängigkeiten: `pip install -r requirements.txt`
4. Kopiere `.env.example` nach `.env` und passe die Werte an
5. Starte den Server: `PYTHONPATH=src uvicorn app.main:app --reload`

## Test

- `pytest`
