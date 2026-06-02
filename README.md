# PlanBar – Schichtplanung für Apotheken

PlanBar ist eine webbasierte Schichtplanungsanwendung für Apotheken (KMU in Deutschland). Sie ermöglicht die Erstellung, Verwaltung und automatische Optimierung von Dienstplänen unter Berücksichtigung des deutschen Arbeitszeitgesetzes (ArbZG).

Das System besteht aus drei Komponenten:

- **PlanBar Backend** – FastAPI-REST-API für Geschäftslogik, Benutzerverwaltung und Persistenz
- **PlanBar Frontend** – React-SPA mit Drag-and-Drop-Kalender und Echtzeit-Status
- **TiTO** (Timetable Optimizer) – Warteschlangen-basierter Optimierer mit Google OR-Tools CP-SAT-Solver

---

## Inhaltsverzeichnis

- [Features](#features)
- [Tech-Stack](#tech-stack)
- [Architektur](#architektur)
- [Quick Start (Lokale Entwicklung)](#quick-start-lokale-entwicklung)
- [Docker Compose (Lokal)](#docker-compose-lokal)
- [Production Deployment](#production-deployment)
  - [Shared Infrastructure](#shared-infrastructure)
  - [Customer Deployment](#customer-deployment)
  - [Deployment-Skript](#deployment-skript)
- [Demo-Instanz](#demo-instanz)
- [Multi-Tenancy](#multi-tenancy)
- [Umgebungsvariablen](#umgebungsvariablen)
- [API-Endpunkte](#api-endpunkte)
- [TiTO-Integrationsfluss](#tito-integrationsfluss)
- [Tests](#tests)
- [CI/CD](#cicd)
- [Backup & Recovery](#backup--recovery)

---

## Features

- **Dashboard** – Übersicht über Mitarbeiter, Schichten heute, offene Anfragen und Dienstpläne
- **Mitarbeiterverwaltung** – CRUD für Mitarbeiter mit Rollen, Farben und Arbeitszeiten
- **Rollenverwaltung** – Definition von Schichtrollen (Früh-/Spät-/Nachtschicht)
- **Schichtwünsche** – Mitarbeiter können Urlaubs-, Bevorzugt- und Nicht-verfügbar-Wünsche einreichen
- **Dienstplanerstellung** – Zwei Modi:
  - *TiTO-gestützt*: Zeitraum + Rollenanforderungen definieren, automatisch optimieren lassen
  - *Manuell*: Drag-and-Drop-Schichtzuweisung im interaktiven Kalender
- **Status-Management** – Entwurf → eingereicht → abgeschlossen/fehlgeschlagen, mit Wiederholungsfunktion
- **Automatische Optimierung** – Beachtet ArbZG (11h Ruhezeit, max. 10h Arbeitstag, Sonntagsruhe etc.)
- **Admin-Bereich** – Benutzerverwaltung, Rollen-Rechte
- **Dark Mode** – Unterstützt helles/dunkles Thema

---

## Tech-Stack

| Komponente | Technologie | Version |
|---|---|---|
| **Frontend** | React 18 + TypeScript | 18.3.1 |
| | Vite | 6.x |
| | Tailwind CSS 4 + shadcn/ui | 4.x |
| | react-dnd, recharts, date-fns | aktuell |
| **Backend** | Python 3.11+ | ≥3.11 |
| | FastAPI + SQLAlchemy + Alembic | aktuell |
| | PostgreSQL 15 / SQLite | 15 |
| | JWT (HttpOnly-Cookies), bcrypt | – |
| **TiTO** | Python 3.11+ | ≥3.11 |
| | Flask + Gunicorn | aktuell |
| | Google OR-Tools CP-SAT | 9.15 |
| | PostgreSQL 15 | 15 |
| **Infrastruktur** | Docker + Docker Compose | – |
| | Caddy (Reverse Proxy, SSL) | – |
| | GitHub Container Registry (GHCR) | – |

---

## Architektur

```
                    ┌─────────────────────────────┐
                    │   PlanBar Frontend (React)   │
                    │   :5173 (dev) / :80 (prod)   │
                    └──────────┬──────────────────┘
                               │ HTTP /api/*
                               ▼
                    ┌─────────────────────────────┐
                    │   PlanBar Backend (FastAPI)  │
                    │   :8000                      │
                    │                              │
                    │  schedule_service.py         │
                    │  tito_proxy.py  ──── HTTP ──────┐
                    │  tito_callback.py ←── HTTP ─────┐│
                    └──────┬───────────────────────┘  ││
                           │ PostgreSQL                ││
                    ┌──────┴─────────┐  ┌──────────────┴┴──────────┐
                    │  planbar_db    │  │  TiTO (Flask :5001)       │
                    │  users         │  │  + Worker × N             │
                    │  employees     │  │  + OR-Tools Solver        │
                    │  schedules     │  │  + PostgreSQL Queue       │
                    │  shiftplans    │  └───────────────────────────┘
                    └────────────────┘
```

### TiTO-Integrationsfluss

1. Benutzer erstellt Dienstplan (Zeitraum + Rollenanforderungen)
2. Plan wird als "Entwurf" gespeichert
3. Admin reicht Plan bei TiTO ein → `POST /schedules/{id}/submit`
4. Backend baut JSON-Payload (Mitarbeiter, Schichtvorlagen, Wünsche, Anforderungen, Callback-URL)
5. `tito_proxy` sendet `POST /jobs` an TiTO-API
6. TiTO reiht den Job in die Warteschlange ein (PostgreSQL `job_queue`)
7. TiTO-Worker holt Job ab, führt OR-Tools-Optimierung aus
8. Nach Abschluss: Callback `POST {callback_url}/api/v1/callbacks/tito`
9. Backend verarbeitet Ergebnis: Status aktualisieren, Shiftplans anlegen
10. Frontend zeigt Ergebnis an (Polling)

---

## Quick Start (Lokale Entwicklung)

### Voraussetzungen

- Python 3.11+
- Node.js 22+
- pnpm (`npm install -g pnpm`)
- PostgreSQL (optional – SQLite funktioniert lokal)

### 1. Backend starten

```bash
cd "PlanBar - Backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env anpassen (SECRET_KEY setzen)
PYTHONPATH=src uvicorn app.main:app --reload
# → http://localhost:8000
```

### 2. Frontend starten

```bash
cd "PlanBar - Frontend"
pnpm install
cp .env.development .env
pnpm dev
# → http://localhost:5173 (proxied /api → localhost:8000)
```

### 3a. TiTO (API-Modus)

```bash
cd TiTO
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py --mode api --port 5001
# → http://localhost:5001
```

### 3b. TiTO (Worker-Modus, separates Terminal)

```bash
cd TiTO
source .venv/bin/activate
python main.py --mode worker
```

---

## Docker Compose (Lokal)

Der klassische Entwicklungs-Stapel (alle Services in einem Compose-File):

```bash
cd Infrastructure
cp .env.example .env    # Passwörter setzen
docker compose up -d
```

Das startet:

| Service | Port | Beschreibung |
|---------|------|-------------|
| `planbar_frontend` | 5173 → 80 | nginx + React-SPA |
| `planbar_backend` | 8000 | FastAPI |
| `tito` | 5001 | Flask-API |
| `tito_worker` ×2 | – | OR-Tools Worker |
| `db` | 5432 | PostgreSQL (TiTO) |
| `db_backend` | 5433 | PostgreSQL (PlanBar) |

---

## Production Deployment

Die Produktionsarchitektur basiert auf **Database-per-Tenant mit Shared PostgreSQL**. Alle Kunden teilen sich zwei PostgreSQL-Instanzen (eine für PlanBar, eine für TiTO), haben aber jeweils eigene Datenbanken und eigene Anwendungs-Container.

### Architektur (VPS)

```
VPS (8 GB RAM, 4+ Cores)
─────────────────────────

Caddy (Port 80 → 443, Let's Encrypt)
├── kunde1.app.planbar.de → localhost:8081
├── kunde2.app.planbar.de → localhost:8082
├── demo.app.planbar.de   → localhost:8090
└── app.planbar.de        → redirect demo

Shared PostgreSQL (Infra-Stack)
├── db_planbar (Port 5432)
│   ├── kunde1_planbar
│   ├── kunde2_planbar
│   └── demo_planbar
└── db_tito (Port 5433)
    ├── kunde1_tito
    ├── kunde2_tito
    └── demo_tito

Per-Customer Stacks
├── Kunde 1 (planbar-kunde1)
│   ├── planbar_frontend (Port 8081)
│   ├── planbar_backend (Port 8001)
│   ├── tito (Port 5001)
│   └── tito_worker ×2
├── Kunde 2 (planbar-kunde2)
│   ├── planbar_frontend (Port 8082)
│   ├── planbar_backend (Port 8002)
│   ├── tito (Port 5002)
│   └── tito_worker ×2
└── Demo ...
```

### Systemvoraussetzungen

| Ressource | 1 Kunde | 5 Kunden | 10 Kunden |
|-----------|---------|----------|-----------|
| RAM idle | ~1,1 GB | ~2,8 GB | ~4,8 GB |
| RAM peak | ~2,5 GB | ~6,0 GB | ~10,5 GB |
| CPU peak | ~3 Cores | ~8 Cores | ~15 Cores |
| Disk | ~3 GB | ~15 GB | ~28 GB |

### 1. Shared Infrastructure starten

```bash
# Auf dem VPS
git clone <repo> /opt/planbar
cd /opt/planbar/Infrastructure

# Passwörter generieren
echo "PLANBAR_SUPER_PASSWORD=$(openssl rand -hex 32)" > .env.infra
echo "TITO_SUPER_PASSWORD=$(openssl rand -hex 32)" >> .env.infra

# Shared PostgreSQL starten (einmalig)
docker compose -f docker-compose.infra.yaml --env-file .env.infra up -d
```

### 2. Caddy Reverse Proxy einrichten

```bash
# Caddy auf dem Host installieren
apt install caddy

cat > /etc/caddy/Caddyfile << 'EOF'
{
    email admin@mphion.de
}

app.planbar.de {
    redir https://demo.app.planbar.de{uri}
}

demo.app.planbar.de {
    reverse_proxy localhost:8090
}

kunde1.app.planbar.de {
    reverse_proxy localhost:8081
}
EOF

systemctl enable --now caddy
```

### 3. Customer deployen

Jeder Kunde bekommt einen eigenen Stack (Frontend, Backend, TiTO, Worker), der sich mit den Shared-DBs verbindet:

```bash
cd /opt/planbar/Infrastructure

# Automatisch (empfohlen)
./scripts/deploy-customer.sh kunde1 8081 5001 8001

# Oder manuell
export CUSTOMER=kunde1 \
  FRONTEND_PORT=8081 \
  TITO_PORT=5001 \
  BACKEND_PORT=8001 \
  DOMAIN=kunde1.app.planbar.de \
  PLANBAR_DB_NAME=kunde1_planbar \
  TITO_DB_NAME=kunde1_tito \
  PLANBAR_DB_PASSWORD=$(openssl rand -hex 32) \
  TITO_DB_PASSWORD=$(openssl rand -hex 32) \
  SECRET_KEY=$(openssl rand -hex 32) \
  TITO_API_KEY=$(openssl rand -hex 16) \
  TITO_JWT_SECRET=$(openssl rand -hex 32)

docker compose -f docker-compose.customer.yaml -p "planbar-${CUSTOMER}" up -d
```

Das Skript `deploy-customer.sh` erledigt automatisch:
- Secrets generieren und in `customers/<kunde>/.env` speichern
- Datenbanken in den Shared-PostgreSQL-Instanzen anlegen (`kunde_planbar`, `kunde_tito`)
- TiTO-Schema in der Kundendatenbank initialisieren
- Caddy-Konfiguration um Subdomain-Eintrag erweitern
- Docker-Stack pullen und starten

### 4. Updaten eines Kunden

```bash
cd /opt/planbar
docker compose \
  -f docker-compose.customer.yaml \
  --env-file customers/kunde1/.env \
  -p planbar-kunde1 \
  pull
docker compose \
  -f docker-compose.customer.yaml \
  --env-file customers/kunde1/.env \
  -p planbar-kunde1 \
  up -d
```

### CI/CD – Automatisiertes Deployment

Bei jedem Push auf `main`:
1. CI baut und pushed Docker-Images zu GHCR
2. Deploy-Worklog SSHt auf den VPS
3. Shared Infrastructure wird geupdated
4. Alle Kunden-Stacks pullen das neue `latest`-Image
5. Demo-Instanz wird geupdated und neu geseedet

Siehe `.github/workflows/deploy.yml`.

---

## Demo-Instanz

Die Demo-Instanz läuft parallel auf dem Produktions-VPS unter `demo.app.planbar.de` und verwendet denselben Mechanismus wie ein normaler Kunden-Stack.

### Besonderheiten

- **Port**: 8090 (separat von Production-Kunden)
- **Domain**: `demo.app.planbar.de`
- **Demo-Credentials** werden auf der Login-Seite angezeigt:
  - Administrator: `admin@mphion.de`
  - Mitarbeiter: `demo@mphion.de`
- **Seed-Daten**: 5 Demo-Mitarbeiter, 3 Rollen (Früh-/Spät-/Nachtschicht)

### Aktivierung

```bash
cd /opt/planbar/Infrastructure
./scripts/deploy-customer.sh demo 8090 5000 8000

# Demo-Seed-Daten einspielen (idempotent)
docker exec -i db_planbar psql -U planbar -d demo_planbar \
  < Infrastructure/init-demo-data.sql
```

Die Demo-Credentials werden über `VITE_SHOW_DEMO_CREDENTIALS=true` in der Frontend-Umgebung aktiviert. In der `docker-compose.customer.yaml` wird dies per Environment-Variable im Frontend-Container gesetzt.

---

## Multi-Tenancy

### Strategie: Database-per-Tenant

Jeder Kunde wird durch eine Kombination aus **eigenen Datenbanken** und **eigenem Anwendungs-Stack** isoliert:

| Aspekt | Isolation |
|--------|-----------|
| **Daten** | Getrennte PostgreSQL-Datenbanken (`kunde1_planbar`, `kunde2_planbar`, …) |
| **Anwendung** | Eigener Docker-Stack (Backend, Frontend, TiTO, Worker) |
| **Netzwerk** | Alle Stacks teilen sich das `planbar_shared` Docker-Netzwerk |
| **Domain** | Eigene Subdomain pro Kunde |
| **Secrets** | Eigene `.env`-Datei pro Kunde (DB-Passwörter, SECRET_KEY, API-Keys) |

### Warum Database-per-Tenant?

- **Keine Code-Änderungen** an Models oder Queries nötig (kein `tenant_id`-Refactoring)
- **Volle Isolation**: Ein Kunde kann keine Daten eines anderen Kunden sehen
- **Einfaches Backup/Restore**: `pg_dump` pro Kundendatenbank
- **Getrennte Ressourcen-Limits**: Jeder Stack hat eigene Docker-Resource-Limits

### Tenant-Lebenszyklus

```bash
# Neuen Kunden anlegen
./Infrastructure/scripts/deploy-customer.sh neukunde 8085 5005 8005

# Kunden-Datenbank sichern
./Infrastructure/scripts/backup.sh

# Kunden-Datenbank wiederherstellen
./Infrastructure/scripts/restore.sh neukunde /backups/neukunde_planbar-20260601.dump

# Kunden entfernen (Vorsicht!)
docker compose -p planbar-neukunde down -v
docker exec db_planbar psql -U planbar -c "DROP DATABASE neukunde_planbar;"
docker exec db_tito psql -U tito -c "DROP DATABASE neukunde_tito;"
```

---

## Umgebungsvariablen

### PlanBar Backend

| Variable | Standard | Beschreibung |
|----------|----------|-------------|
| `DATABASE_URL` | `sqlite:///./planbar.db` | Datenbank-Connection-String |
| `SECRET_KEY` | *(required)* | JWT-Signierschlüssel (Production: `openssl rand -hex 32`) |
| `JWT_ALGORITHM` | `HS256` | JWT-Algorithmus |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access-Token-Laufzeit |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh-Token-Laufzeit |
| `TITO_API_URL` | `http://localhost:5001` | TiTO-API-Endpunkt |
| `BACKEND_CALLBACK_URL` | `http://localhost:8000` | Callback-URL für TiTO |
| `TITO_API_KEY` | *(optional)* | API-Key für TiTO-Authentifizierung |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Erlaubte CORS-Origins |
| `ENVIRONMENT` | `development` | Umgebung (`development/test/staging/production/demo`) |
| `LOG_LEVEL` | `INFO` | Log-Level |

### PlanBar Frontend

| Variable | Standard | Beschreibung |
|----------|----------|-------------|
| `VITE_API_URL` | `/api/v1` | Backend-API-Base-URL |
| `VITE_SHOW_DEMO_CREDENTIALS` | `false` | Demo-Zugangsdaten anzeigen |
| `VITE_DEMO_ADMIN_PASSWORD` | – | Anzuzeigendes Admin-Passwort |
| `VITE_DEMO_USER_PASSWORD` | – | Anzuzeigendes User-Passwort |

### TiTO

Siehe `TiTO/.env.example` für alle TiTO-spezifischen Variablen (Datenbank, Queue, Retry, JWT etc.).

### Infrastructure (Shared)

| Variable | Beschreibung |
|----------|-------------|
| `PLANBAR_SUPER_PASSWORD` | PostgreSQL-Passwort für `planbar`-Superuser |
| `TITO_SUPER_PASSWORD` | PostgreSQL-Passwort für `tito`-Superuser |

### Per-Customer

| Variable | Beschreibung |
|----------|-------------|
| `FRONTEND_PORT` | Host-Port für Frontend (z. B. `8081`) |
| `TITO_PORT` | Host-Port für TiTO-API (z. B. `5001`) |
| `BACKEND_PORT` | Host-Port für Backend (z. B. `8001`) |
| `DOMAIN` | Kundendomäne (z. B. `kunde1.app.planbar.de`) |
| `PLANBAR_DB_NAME` | Kundendatenbank-Name (z. B. `kunde1_planbar`) |
| `TITO_DB_NAME` | TiTO-Datenbank-Name (z. B. `kunde1_tito`) |
| `PLANBAR_DB_PASSWORD` | DB-Passwort für diese Kundendatenbank |
| `TITO_DB_PASSWORD` | TiTO-DB-Passwort |
| `SECRET_KEY` | JWT-Secret für dieses Backend |
| `TITO_API_KEY` | TiTO-API-Key |
| `TITO_JWT_SECRET` | TiTO-JWT-Secret |

---

## API-Endpunkte

### PlanBar Backend (`/api/v1`)

| Methode | Pfad | Beschreibung | Auth |
|---------|------|-------------|------|
| GET | `/health/ping` | Basis-Healthcheck | – |
| POST | `/users/login` | Login (setzt HttpOnly-Cookies) | – |
| POST | `/users/refresh-token` | Token erneuern | – |
| POST | `/users/logout` | Logout | User |
| GET | `/users/me` | Eigenes Profil | User |
| PUT | `/users/me/password` | Passwort ändern | User |
| GET | `/users` | Benutzer auflisten | Admin |
| CRUD | `/users/{id}` | Benutzer verwalten | Admin |
| CRUD | `/employees` | Mitarbeiter verwalten | User/Admin |
| CRUD | `/roles` | Rollen verwalten | User/Admin |
| CRUD | `/requests` | Schichtwünsche | User |
| CRUD | `/schedules` | Dienstpläne | User/Admin |
| POST | `/schedules/{id}/submit` | An TiTO übermitteln | Admin |
| POST | `/schedules/{id}/retry` | Wiederholen | Admin |
| PUT | `/schedules/{id}/shifts` | Schichten bearbeiten | User |
| POST | `/callbacks/tito` | TiTO-Callback | Intern |

### TiTO

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| GET | `/health` | Healthcheck |
| GET | `/jobs` | Alle Jobs auflisten |
| POST | `/jobs` | Job einreihen |
| GET | `/jobs/{id}` | Job-Status abrufen |
| POST | `/jobs/{id}/retry` | Job wiederholen |
| GET | `/dlq` | Dead Letter Queue |
| POST | `/workers/register` | Worker registrieren |
| POST | `/workers/heartbeat` | Heartbeat senden |

---

## Tests

### Backend (171 Tests)

```bash
cd "PlanBar - Backend"
pip install -e ".[testing]"
pytest
```

### TiTO (40 Tests)

```bash
cd TiTO
pip install -r requirements.txt
pip install -e ".[testing]"
pytest
```

### Frontend (Build-Verifikation)

```bash
cd "PlanBar - Frontend"
pnpm install
pnpm run build
```

---

## CI/CD

Die Pipeline (`.github/workflows/ci.yml`) läuft bei Push/PR auf `dev` und `main`:

1. **Backend** – Tests mit pytest + Coverage
2. **TiTO** – Tests mit pytest
3. **Frontend** – `pnpm run build`
4. **Docker-Build** (nach erfolgreichen Tests, nur Push) – Build & Push zu GHCR:
   - `ghcr.io/marv1101/mvit-planbar/frontend`
   - `ghcr.io/marv1101/mvit-planbar/backend`
   - `ghcr.io/marv1101/mvit-planbar/tito`
   - `ghcr.io/marv1101/mvit-planbar/tito-worker`
   - Tags: `sha-<hash>`, `<branch>`, `latest` (nur main)

Das Deployment (`.github/workflows/deploy.yml`) deployt automatisch auf den VPS bei Push auf `main`.

---

## Backup & Recovery

### Tägliches Backup (Cron)

```bash
# Installieren
cp Infrastructure/scripts/backup.sh /etc/cron.daily/planbar-backup
chmod +x /etc/cron.daily/planbar-backup

# Oder via crontab (3:00 Uhr täglich)
0 3 * * * /opt/planbar/scripts/backup.sh
```

### Wiederherstellung

```bash
./Infrastructure/scripts/restore.sh kunde1 /opt/planbar/backups/kunde1_planbar-20260601.dump
```

### Aufbewahrung

- 30 Tage tägliche Backups
- Backup-Format: PostgreSQL Custom (`pg_dump --format=custom --compress=9`)
- Optional: Sync zu S3-kompatiblem Storage via `rclone`

---

## Projektstruktur

```
mvit PlanBar/
├── .github/workflows/        # CI/CD (ci.yml, deploy.yml)
├── Infrastructure/           # Docker-Compose, Init-Skripte, Deployment
│   ├── docker-compose.infra.yaml     # Shared PostgreSQL
│   ├── docker-compose.customer.yaml  # Per-Customer-Stack
│   ├── scripts/                      # deploy-customer, backup, restore
│   ├── init-db.sql                   # TiTO-Schema
│   ├── init-demo-data.sql            # Demo-Seed-Daten
│   └── .env.example / .env.customer.example
├── PlanBar - Backend/        # FastAPI + SQLAlchemy + Alembic
│   ├── src/app/
│   │   ├── api/v1/           # REST-Endpunkte
│   │   ├── db/models/        # SQLAlchemy-Modelle
│   │   ├── services/         # Business-Logik + TiTO-Integration
│   │   ├── core/             # Auth, Rate-Limiting, Logging
│   │   └── middleware/       # Error-Handler, Request-Logging
│   ├── tests/                # Pytest (171 Tests)
│   └── migrations/           # Alembic-Migrationen
├── PlanBar - Frontend/       # React + Vite + Tailwind
│   ├── src/app/pages/        # Dashboard, Employees, Schedule, …
│   ├── src/app/context/      # AuthContext, AppContext
│   └── nginx.conf            # Production nginx
├── TiTO/                     # Flask + OR-Tools CP-SAT Solver
│   ├── src/tito/
│   │   ├── api.py            # Flask-Routen
│   │   ├── solver.py         # OR-Tools-Modell
│   │   ├── worker.py         # Queue-Consumer
│   │   └── db.py             # Queue-Operationen
│   └── tests/                # Pytest (40 Tests)
├── Docs/
│   ├── production-deployment-plan.md
│   └── go-live-readiness-plan.md
├── .github/workflows/
└── .gitignore
```
