# Production Deployment Plan – mvit PlanBar

**Stand:** 01.06.2026
**Author:** Deployment Planning

---

## Inhaltsverzeichnis

1. [Architektur-Überblick](#1-architektur-überblick)
2. [System Requirements](#2-system-requirements)
3. [VPS-Setup](#3-vps-setup)
4. [Shared Infrastructure (Caddy + PostgreSQL)](#4-shared-infrastructure)
5. [Customer-Deployment-Template](#5-customer-deployment-template)
6. [Demo-Instanz](#6-demo-instanz)
7. [CI/CD – Automatisiertes Deployment](#7-cicd)
8. [Security Härtung (vor Go-Live)](#8-security-härtung)
9. [Backup-Strategie](#9-backup-strategie)
10. [Monitoring & Observability](#10-monitoring)
11. [Zeitplan & Priorisierung](#11-zeitplan)
12. [Anhang: Befehlsreferenz](#12-anhang)

---

## 1. Architektur-Überblick

### Ziel

- **Multi-Tenant via Database-per-Tenant:** Jeder Kunde bekommt separate Datenbanken in einer gemeinsamen PostgreSQL-Instanz
- **Subdomain-Routing:** `kunde1.app.planbar.de`, `kunde2.app.planbar.de`, `demo.app.planbar.de`
- **Reverse Proxy:** Caddy mit automatischem Let's Encrypt SSL
- **Demo:** Parallel auf dem gleichen VPS unter `demo.app.planbar.de`

### Aktuelle Codebase (Stand Juni 2026)

```
mvit PlanBar/
├── PlanBar - Backend/     # FastAPI + SQLAlchemy + Alembic
├── PlanBar - Frontend/    # React + Vite + nginx
├── TiTO/                  # Flask + OR-Tools + eigene DB
├── Infrastructure/        # Docker-Compose, Init-Skripte, .env
└── .github/workflows/     # CI (Tests + Docker-Build → GHCR)
```

### Ziel-Architektur

```
VPS1 (stärker – 8 GB RAM, 4+ Cores)
─────────────────────────────────────

Docker-Netzwerk: planbar_shared (extern, 172.20.0.0/16)

┌──────────────────────────────────────┐
│  Caddy Reverse Proxy                 │
│  Port 80 → 443 (Let's Encrypt)       │
│                                      │
│  app.planbar.de → redirect demo      │
│  demo.app.planbar.de → localhost:8090│
│  kunde1.app.planbar.de → :8081       │
│  kunde2.app.planbar.de → :8082       │
│  kundeN.app.planbar.de → :808N       │
└──────────────────────────────────────┘

┌──────────────────────────┐  ┌──────────────────────────┐
│ PostgreSQL: db_planbar   │  │ PostgreSQL: db_tito       │
│ Port 5432 (Container)    │  │ Port 5433 (Container)     │
│ ─────────────────────────│  │ ───────────────────────── │
│ kunde1_planbar           │  │ kunde1_tito               │
│ kunde2_planbar           │  │ kunde2_tito               │
│ demo_planbar             │  │ demo_tito                 │
│ (weitere pro Kunde)      │  │ (weitere pro Kunde)       │
└──────────────────────────┘  └──────────────────────────┘

┌────── Kunde 1 ──────┐  ┌────── Kunde 2 ──────┐
│ planbar_backend:8081│  │ planbar_backend:8082│
│ tito:5001           │  │ tito:5002           │
│ tito_worker ×2      │  │ tito_worker ×2      │
│ planbar_frontend    │  │ planbar_frontend    │
│ (intern nginx:80)   │  │ (intern nginx:80)   │
└─────────────────────┘  └─────────────────────┘
```

### Entscheidungen

| Aspekt | Entscheidung | Begründung |
|--------|-------------|------------|
| Multi-Tenancy | Database-per-Tenant | Keine Code-Änderungen an Models nötig, saubere Isolation |
| DB-Isolation | Shared PostgreSQL, separate DBs | Spart ~1 GB RAM gegenüber Container-pro-Kunde |
| Reverse Proxy | Caddy | Automatisches SSL, einfache Config, HTTP/3 |
| Domain-Schema | Subdomain pro Kunde | Sauber, einfach per Wildcard-DNS `*.app.planbar.de` |
| Demo | Gleicher VPS, eigener Port | Spart zweiten VPS, kein Performance-Problem |
| Deployment | Docker Compose (parametrisiert) | Einfach, überschaubar für 5–10 Kunden |

---

## 2. System Requirements

### Pro Kunden-Stack

| Service | Image | RAM (idle) | RAM (peak) | CPU (peak) | Disk |
|---------|-------|-----------|-----------|-----------|------|
| PostgreSQL 15 (PlanBar) | `postgres:15-alpine` | 200 MB | 500 MB | 0.5 core | ~2 GB |
| PostgreSQL 15 (TiTO) | `postgres:15-alpine` | 150 MB | 400 MB | 0.5 core | ~200 MB |
| FastAPI Backend | `python:3.11-slim` | 120 MB | 300 MB | 0.5 core | 200 MB |
| TiTO API (Gunicorn) | `python:3.11-slim` | 150 MB | 400 MB* | 1.0 core* | 200 MB |
| TiTO Worker ×2 | `python:3.11-slim` | 100 MB ×2 | 300 MB ×2 | 0.5 core ×2 | 100 MB |
| nginx Frontend | `nginx:stable-alpine` | 30 MB | 50 MB | <0.1 core | 50 MB |
| Caddy | `caddy:alpine` | 20 MB | 40 MB | <0.1 core | 10 MB |
| **Gesamt (shared DBs)** | | **~870 MB** | **~2.3 GB** | **~3 cores** | **~3 GB** |

*OR-Tools CP-SAT Solver verursacht CPU-Spikes für Sekunden bis Minuten während der Schichtplan-Optimierung. Gleichzeitige Optimierungsläufe mehrerer Kunden sind unwahrscheinlich.

### Hochrechnung VPS1

| Kundenanzahl | RAM idle | RAM peak (gleichzeitig) | CPU (Basis) | Disk |
|-------------|----------|----------------------|------------|------|
| 1 + Demo | ~1,2 GB | ~2,8 GB | ~3 cores | ~5 GB |
| 5 | ~2,8 GB | ~6,0 GB | ~5 cores | ~15 GB |
| 8 | ~4,0 GB | ~8,5 GB | ~8 cores | ~22 GB |
| 10 | ~4,8 GB | ~10,5 GB | ~10 cores | ~28 GB |

**Empfehlung VPS1:** 8 GB RAM, 6 Cores, 50 GB SSD → 5–8 Kunden + Demo stabil.
**VPS2 (Staging):** 4 GB RAM, 2 Cores → ausreichend für Test-Deployments.

---

## 3. VPS-Setup - erledigt

### 3.1 Grundinstallation

```bash
# System aktualisieren
apt update && apt upgrade -y
apt install -y curl ufw unattended-upgrades

# Docker installieren
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# Docker Compose Plugin installieren
apt install -y docker-compose-plugin

# Benutzer einrichten
adduser planbar
usermod -aG docker planbar

# Firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Automatische Sicherheitsupdates
dpkg-reconfigure --priority=low unattended-upgrades
```

### 3.2 Caddy installieren und konfigurieren

```bash
# Caddy installieren
apt install -y caddy

# Caddyfile
cat > /etc/caddy/Caddyfile << 'CADDY'
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

kunde2.app.planbar.de {
    reverse_proxy localhost:8082
}
CADDY

systemctl enable --now caddy
```

### 3.3 Projektstruktur auf dem VPS

```
/opt/planbar/
├── docker-compose.infra.yaml   # Caddy + PostgreSQL shared
├── docker-compose.customer.yaml # Customer-Template
├── .env.infra                   # Secrets für Infra
├── customers/
│   ├── kunde1/
│   │   ├── .env                 # Kundenspezifische Secrets
│   │   └── compose.override.yaml
│   ├── kunde2/
│   │   ├── .env
│   │   └── compose.override.yaml
│   └── demo/
│       ├── .env
│       └── compose.override.yaml
├── backups/                     # Tägliche DB-Dumps
├── scripts/
│   ├── deploy-customer.sh       # Neuen Kunden deployen
│   ├── backup.sh                # DB-Backup
│   └── demo-seed.sh             # Demo-Daten einspielen
└── caddy/
    └── Caddyfile                # Wird von Caddy-Service genutzt
```

---

## 4. Shared Infrastructure

### 4.1 `docker-compose.infra.yaml`

```yaml
services:
  db_planbar:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: planbar
      POSTGRES_PASSWORD: ${PLANBAR_SUPER_PASSWORD}
    volumes:
      - planbar_postgres_data:/var/lib/postgresql/data
      - ./init-multi-db-planbar.sh:/docker-entrypoint-initdb.d/init.sh:ro
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U planbar"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - planbar_shared

  db_tito:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: tito
      POSTGRES_PASSWORD: ${TITO_SUPER_PASSWORD}
    volumes:
      - tito_postgres_data:/var/lib/postgresql/data
      - ./init-multi-db-tito.sh:/docker-entrypoint-initdb.d/init.sh:ro
    ports:
      - "127.0.0.1:5433:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tito"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - planbar_shared

networks:
  planbar_shared:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  planbar_postgres_data:
  tito_postgres_data:
```

### 4.2 Init-Skripte für neue Kundendatenbanken

**`init-multi-db-planbar.sh`:**
```bash
#!/bin/bash
# Wird beim ersten Start von PostgreSQL ausgeführt.
# Neue Kundendatenbanken werden per Skript oder manuell angelegt:
# CREATE DATABASE kundeN_planbar OWNER planbar;
```

**`init-multi-db-tito.sh`:**
```bash
#!/bin/bash
# Gleiches Prinzip für TiTO-Datenbanken
```

Neue Datenbank wird pro Kunde angelegt:
```bash
# Bei neuer Kundenaufnahme
docker exec -i db_planbar psql -U planbar -c "CREATE DATABASE kunde3_planbar;"
docker exec -i db_tito psql -U tito -c "CREATE DATABASE kunde3_tito;"
# TiTO-Schema einspielen
docker exec -i db_tito psql -U tito -d kunde3_tito < Infrastructure/init-db.sql
```

---

## 5. Customer-Deployment-Template

### 5.1 `docker-compose.customer.yaml`

```yaml
services:
  tito:
    image: ghcr.io/marv1101/mvit-planbar/tito:latest
    ports:
      - "127.0.0.1:${TITO_PORT}:5001"
    environment:
      DATABASE_URL: postgresql://tito:${TITO_DB_PASSWORD}@db_tito:5432/${TITO_DB_NAME}
      QUEUE_TABLE: job_queue
      CALLBACK_QUEUE: callback_queue
      MAX_JOBS: 20
      TIMEOUT_SECONDS: 300
      API_TOKEN: ${TITO_API_KEY}
      JWT_SECRET: ${TITO_JWT_SECRET}
      JWT_ALGORITHM: HS256
    depends_on:
      db_tito:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - planbar_shared

  tito_worker:
    image: ghcr.io/marv1101/mvit-planbar/tito-worker:latest
    deploy:
      mode: replicated
      replicas: 2
    environment:
      DATABASE_URL: postgresql://tito:${TITO_DB_PASSWORD}@db_tito:5432/${TITO_DB_NAME}
      API_URL: http://tito:5001
      QUEUE_TABLE: job_queue
      CALLBACK_QUEUE: callback_queue
      MAX_JOBS: 10
      TIMEOUT_SECONDS: 300
    depends_on:
      db_tito:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - planbar_shared

  planbar_backend:
    image: ghcr.io/marv1101/mvit-planbar/backend:latest
    ports:
      - "127.0.0.1:${BACKEND_PORT}:8000"
    environment:
      DATABASE_URL: postgresql://planbar:${PLANBAR_DB_PASSWORD}@db_planbar:5432/${PLANBAR_DB_NAME}
      SECRET_KEY: ${SECRET_KEY}
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 10
      REFRESH_TOKEN_EXPIRE_DAYS: 90
      TITO_API_URL: http://tito:5001
      TITO_API_KEY: ${TITO_API_KEY}
      BACKEND_CALLBACK_URL: https://${DOMAIN}/api/v1
      CORS_ORIGINS: https://${DOMAIN}
      ENVIRONMENT: production
      LOG_LEVEL: INFO
    depends_on:
      db_planbar:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/ping"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 15s
    networks:
      - planbar_shared

  planbar_frontend:
    image: ghcr.io/marv1101/mvit-planbar/frontend:latest
    ports:
      - "${FRONTEND_PORT}:80"
    environment:
      BACKEND_URL: http://planbar_backend:8000
    depends_on:
      planbar_backend:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - planbar_shared

networks:
  planbar_shared:
    external: true
```

### 5.2 Deployment-Skript

**`scripts/deploy-customer.sh`:**
```bash
#!/bin/bash
set -euo pipefail

CUSTOMER="${1:?Usage: $0 <customer-id> [frontend-port] [tito-port] [backend-port]}"
FRONTEND_PORT="${2:-8080}"
TITO_PORT="${3:-5000}"
BACKEND_PORT="${4:-8000}"
DOMAIN="${CUSTOMER}.app.planbar.de"

CUSTOMER_DIR="/opt/planbar/customers/${CUSTOMER}"

if [ -d "$CUSTOMER_DIR" ]; then
  echo "Customer ${CUSTOMER} already exists. Updating..."
else
  echo "Creating customer ${CUSTOMER}..."
  mkdir -p "$CUSTOMER_DIR"

  # Secrets generieren
  cat > "${CUSTOMER_DIR}/.env" << EOF
FRONTEND_PORT=${FRONTEND_PORT}
TITO_PORT=${TITO_PORT}
BACKEND_PORT=${BACKEND_PORT}
DOMAIN=${DOMAIN}

PLANBAR_DB_NAME=${CUSTOMER}_planbar
TITO_DB_NAME=${CUSTOMER}_tito

PLANBAR_DB_PASSWORD=$(openssl rand -hex 32)
TITO_DB_PASSWORD=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
TITO_API_KEY=$(openssl rand -hex 16)
TITO_JWT_SECRET=$(openssl rand -hex 32)
EOF

  # Datenbanken anlegen
  docker exec -i db_planbar psql -U planbar -c "CREATE DATABASE ${CUSTOMER}_planbar;"
  docker exec -i db_tito psql -U tito -c "CREATE DATABASE ${CUSTOMER}_tito;"
  docker exec -i db_tito psql -U tito -d "${CUSTOMER}_tito" < /opt/planbar/Infrastructure/init-db.sql

  # Caddy-Eintrag hinzufügen
  echo "${DOMAIN} {
    reverse_proxy localhost:${FRONTEND_PORT}
}" >> /etc/caddy/Caddyfile
  systemctl reload caddy
fi

# Stack starten/updaten
docker compose \
  -f /opt/planbar/docker-compose.customer.yaml \
  --env-file "${CUSTOMER_DIR}/.env" \
  -p "planbar-${CUSTOMER}" \
  up -d

echo "✅ Customer ${CUSTOMER} deployed at https://${DOMAIN}"
```

### 5.3 Nötige Code-Änderungen am Projekt

| Datei | Änderung | Status |
|-------|----------|--------|
| `Infrastructure/compose.yaml` | In zwei Dateien aufteilen: `.infra.yaml` (DBs) + `.customer.yaml` (Template) | ⬜ Offen |
| `Infrastructure/init-db.sql` | Muss in `docker-compose.customer.yaml` per Init-Skript geladen werden | ⬜ Offen |
| `PlanBar - Backend/Dockerfile` | Pfad prüfen: `COPY src/app ./app` → ggf. korrigieren | ⬜ Offen |
| `PlanBar - Backend/src/app/config.py` | `secret_key: str = Field(...)` ohne Default, Production-Guard | ⬜ Offen |
| `PlanBar - Frontend/nginx.conf` | Security Headers ergänzen | ⬜ Offen |
| `PlanBar - Frontend/docker-entrypoint.sh` | Ggf. für Prod-Umgebungen anpassen | ⬜ Offen |
| `.github/workflows/ci.yml` | Deploy-Job ergänzen | ⬜ Offen |

---

## 6. Demo-Instanz

### 6.1 Konfiguration

Die Demo-Instanz nutzt das gleiche Customer-Template, aber mit:

```bash
# Deployment
./scripts/deploy-customer.sh demo 8090 5000 8000

# Demo-spezifische Overrides
cat > /opt/planbar/customers/demo/compose.override.yaml << 'EOF'
services:
  planbar_backend:
    environment:
      ENVIRONMENT: demo
  planbar_frontend:
    environment:
      BACKEND_URL: http://planbar_backend:8000
EOF

docker compose \
  -f /opt/planbar/docker-compose.customer.yaml \
  -f /opt/planbar/customers/demo/compose.override.yaml \
  --env-file /opt/planbar/customers/demo/.env \
  -p "planbar-demo" \
  up -d
```

### 6.2 Demo-Seed-Daten

```sql
-- scripts/demo-seed.sql
-- Demo-Daten für Präsentationszwecke
INSERT INTO employees (name, color, user_id) VALUES
  ('Max Mustermann', '#3b82f6', 1),
  ('Erika Musterfrau', '#ef4444', 1),
  ('John Doe', '#22c55e', 1),
  ('Jane Smith', '#f59e0b', 1),
  ('Anna Schmidt', '#8b5cf6', 1);
-- ... weitere Demo-Daten
```

### 6.3 Frontend Demo-Credentials

In `PlanBar - Frontend/.env.production` (neu) oder via Docker-Env:
```
VITE_API_URL=/api/v1
VITE_SHOW_DEMO_CREDENTIALS=false   # Für Kunden-Production
VITE_DEMO_ADMIN_PASSWORD=
VITE_DEMO_USER_PASSWORD=
```

Für Demo-Override:
```
VITE_SHOW_DEMO_CREDENTIALS=true
VITE_DEMO_ADMIN_PASSWORD=demo-admin-2024
VITE_DEMO_USER_PASSWORD=demo-user-2024
```

---

## 7. CI/CD

### 7.1 Aktueller Stand (`.github/workflows/ci.yml`)

- **Trigger:** Push/PR auf `dev` und `main`
- **Jobs:**
  1. `backend` – Tests
  2. `tito` – Tests
  3. `frontend` – Build
  4. `docker-build` (nach allen Tests) – Build & Push zu GHCR
     - Images: `frontend`, `backend`, `tito`, `tito-worker`
     - Tags: `sha-<hash>`, `<branch>`, `latest` (nur main)

### 7.2 Erweiterung um Deployment

**Neue Datei `.github/workflows/deploy.yml`:**

```yaml
name: Deploy

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]

jobs:
  deploy-production:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    strategy:
      matrix:
        customer: ${{ fromJSON(secrets.CUSTOMER_LIST || '["demo"]') }}
    steps:
      - name: Deploy ${{ matrix.customer }}
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS1_HOST }}
          username: ${{ secrets.VPS1_USER }}
          key: ${{ secrets.VPS1_SSH_KEY }}
          script: |
            export COMPOSE_FILE="/opt/planbar/docker-compose.customer.yaml"
            export ENV_FILE="/opt/planbar/customers/${{ matrix.customer }}/.env"
            docker compose \
              -f "$COMPOSE_FILE" \
              --env-file "$ENV_FILE" \
              -p "planbar-${{ matrix.customer }}" \
              pull
            docker compose \
              -f "$COMPOSE_FILE" \
              --env-file "$ENV_FILE" \
              -p "planbar-${{ matrix.customer }}" \
              up -d
```

### 7.3 Deployment-Strategie

| Umgebung | Branch | Trigger | Ziel |
|----------|--------|---------|------|
| **Staging** | `dev` | Push | VPS2 (SSH + docker compose) |
| **Production** | `main` | Push (nach CI) | VPS1 (SSH + docker compose) |
| **Demo** | `main` | Push | VPS1 (separater Stack) |

**Image-Tagging:**
- `dev` → Images mit Tag `dev` für Staging
- `main` → Images mit Tag `latest` für Production
- Optional: Pro Kunde fixierter Tag (`kunde1-v2.3.0`) für kontrollierte Rollouts

---

## 8. Security Härtung - erledigt

Referenz: `Docs/go-live-readiness-plan.md` – Phase 0

### Kritisch (vor erstem Deployment)

| ID | Maßnahme | Datei | Aufwand |
|----|---------|-------|---------|
| S1 | Secrets aus Git-History entfernen | `Infrastructure/.env`, `PlanBar - Backend/.env` | 1 h |
| S2 | `SECRET_KEY` als Required ohne Default | `PlanBar - Backend/src/app/config.py` | 30 min |
| S3 | Production-Guard bei Start | `PlanBar - Backend/src/app/main.py` | 30 min |
| S4 | `.gitignore` fixen (`.env`-Dateien) | `.gitignore` | 10 min |

### Hoch

| ID | Maßnahme | Datei | Aufwand |
|----|---------|-------|---------|
| S5 | nginx Security Headers | `PlanBar - Frontend/nginx.conf` | 30 min |
| S6 | Alembic-Migrationen finalisieren | `alembic.ini`, `main.py` | 2 h |
| S7 | CORS in Production auf konkrete Domain setzen | `config.py`, `.env` | 15 min |

### Mittel (nach Go-Live)

| ID | Maßnahme | Datei | Aufwand |
|----|---------|-------|---------|
| S8 | Log-Level via Env (`LOG_LEVEL`) | `PlanBar - Backend/src/app/core/logging.py` | 30 min |
| S9 | Strukturiertes JSON-Logging | `PlanBar - Backend/src/app/core/logging.py` | 1 h |
| S10 | Request-ID / Correlation-ID | `PlanBar - Backend/src/app/main.py` | 30 min |

### Umsetzung S2 + S3: `config.py` Production-Guard

```python
# config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field("sqlite:///./planbar.db")
    secret_key: str = Field(...)  # KEIN Default mehr!
    jwt_algorithm: str = Field("HS256")
    access_token_expire_minutes: int = Field(15)
    refresh_token_expire_days: int = Field(7)
    tito_api_url: str = Field("http://localhost:5001")
    backend_callback_url: str = Field("http://localhost:8000")
    cors_origins: str = Field("http://localhost:5173,http://localhost:3000")
    tito_api_key: str | None = Field(None)

settings = Settings()
```

```python
# main.py (nach App-Erstellung)
if settings.environment in ("production", "demo"):
    assert settings.secret_key not in ("change-me-in-production", "", None), \
        "SECRET_KEY must be set in production"
```

### Umsetzung S5: nginx Security Headers

```nginx
# In PlanBar - Frontend/nginx.conf
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "0" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://${BACKEND_URL}" always;
```

---

## 9. Backup-Strategie

### 9.1 Datenbank-Backup

```bash
# scripts/backup.sh
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/planbar/backups"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d-%H%M)
LOG_FILE="${BACKUP_DIR}/backup-${DATE}.log"

exec 2>&1 > "${LOG_FILE}"

echo "[$(date)] Starting backup..."

# Alle PlanBar-Datenbanken sichern
for db in $(docker exec db_planbar psql -U planbar -t -c "SELECT datname FROM pg_database WHERE datname LIKE '%_planbar';"); do
  if [ -n "$db" ]; then
    echo "Backing up ${db}..."
    docker exec db_planbar pg_dump -U planbar -d "$db" \
      --format=custom \
      --compress=9 \
      --file="/tmp/${db}.dump"
    docker cp "db_planbar:/tmp/${db}.dump" "${BACKUP_DIR}/${db}-${DATE}.dump"
    docker exec db_planbar rm "/tmp/${db}.dump"
  fi
done

# Alle TiTO-Datenbanken sichern
for db in $(docker exec db_tito psql -U tito -t -c "SELECT datname FROM pg_database WHERE datname LIKE '%_tito';"); do
  if [ -n "$db" ]; then
    echo "Backing up ${db}..."
    docker exec db_tito pg_dump -U tito -d "$db" \
      --format=custom \
      --compress=9 \
      --file="/tmp/${db}.dump"
    docker cp "db_tito:/tmp/${db}.dump" "${BACKUP_DIR}/${db}-${DATE}.dump"
    docker exec db_tito rm "/tmp/${db}.dump"
  fi
done

# Alte Backups löschen
find "${BACKUP_DIR}" -name "*.dump" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name "*.log" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup complete."
```

### 9.2 Cron-Job

```bash
# Täglich um 3:00 Uhr
0 3 * * * /opt/planbar/scripts/backup.sh

# Optional: Backup auf S3-kompatiblen Storage (z. B. Backblaze B2, Wasabi)
# Voraussetzung: rclone installiert und konfiguriert
30 3 * * * rclone sync /opt/planbar/backups/ remote:planbar-backups/
```

### 9.3 Wiederherstellung

```bash
# Einzelne Datenbank wiederherstellen
docker exec -i db_planbar pg_restore -U planbar -d kunde1_planbar \
  --clean --if-exists < backups/kunde1_planbar-20260601-0300.dump

# Nach Wiederherstellung: Backend + TiTO neustarten
docker compose -f docker-compose.customer.yaml \
  --env-file customers/kunde1/.env \
  -p planbar-kunde1 \
  restart planbar_backend tito
```

---

## 10. Monitoring

### 10.1 Gesundheit (Healthchecks)

Alle Services haben bereits Healthchecks (siehe `docker-compose.customer.yaml`). Docker restartet Container automatisch bei Fehlschlag.

```bash
# Status aller Stacks
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep planbar

# Logs eines Kunden-Stacks
docker compose -p planbar-kunde1 logs --tail=50 -f
```

### 10.2 Error-Tracking (optional, nach Go-Live)

**Backend (Sentry):**
```python
# pip install sentry-sdk
# In main.py:
import sentry_sdk
sentry_sdk.init(
    dsn=settings.sentry_dsn,
    environment=settings.environment,
    traces_sample_rate=0.1,
)
```

**Frontend (Sentry):**
```typescript
// pnpm add @sentry/react
import * as Sentry from '@sentry/react';
Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.VITE_ENVIRONMENT,
});
```

### 10.3 Ressourcen-Überwachung

```bash
# Einfach: docker stats laufen lassen
docker stats --no-stream

# Oder: ctop (interaktives Monitoring für Container)
# https://github.com/bcicen/ctop

# Basis-System-Monitoring via htop + df -h
apt install htop
```

### 10.4 Docker Resource Limits (pro Kunden-Stack)

```yaml
# In compose.override.yaml für Production
services:
  planbar_backend:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
  tito:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
  tito_worker:
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.5"
```

---

## 11. Zeitplan

### Phasen & Aufwand

| Phase | Beschreibung | Aufwand | Priority |
|-------|-------------|---------|----------|
| **1** | VPS-Grundsetup (Docker, Caddy, Firewall) | 1–2 h | ⬜ Phase 0 |
| **2** | Security Härtung (Secrets, Config, nginx) | 3–5 h | 🔴 Kritisch |
| **3** | Infra-Stack (Caddy-Config, Shared-PostgreSQL) | 2–3 h | ⬜ Phase 1 |
| **4** | Customer-Template + Deployment-Skripte | 4–6 h | ⬜ Phase 1 |
| **5** | Demo-Instanz + Seed-Daten | 2–3 h | ⬜ Phase 2 |
| **6** | CI/CD-Deployment-Pipeline | 2–3 h | ⬜ Phase 2 |
| **7** | Backup + Monitoring | 1–2 h | ⬜ Phase 3 |

### Roadmap

```
Woche 1:  ████████████████████░░░░░░░░░░░░░░░░
          Phase 1 + 2 (VPS + Security)

Woche 2:  ░░░░░████████████████████░░░░░░░░░░░
          Phase 3 + 4 (Infra + Customer-Template)

Woche 3:  ░░░░░░░░░░████████████████████░░░░░░
          Phase 5 + 6 (Demo + CI/CD)

Woche 4:  ░░░░░░░░░░░░░░░░░░██████████████████
          Phase 7 (Backup + Monitoring) + Go-Live
```

---

## 12. Anhang

### 12.1 Befehlsreferenz

```bash
# === Deployment ===

# Neuen Kunden anlegen und deployen
./scripts/deploy-customer.sh kunde3 8083 5003 8003

# Bestehenden Kunden updaten (neues Image)
docker compose -f docker-compose.customer.yaml \
  --env-file customers/kunde1/.env \
  -p planbar-kunde1 pull
docker compose -f docker-compose.customer.yaml \
  --env-file customers/kunde1/.env \
  -p planbar-kunde1 up -d

# === Backup ===

# Manuelles Backup
./scripts/backup.sh

# Datenbank-Listing
docker exec db_planbar psql -U planbar -c "\l"

# === Monitoring ===

# Alle Kunden-Stacks
docker ps --format "table {{.Names}}\t{{.Status}}" | grep planbar

# Logs (ein Kunde)
docker compose -p planbar-kunde1 logs --tail=50 -f

# Ressourcen
docker stats --no-stream | grep planbar

# === Notfall ===

# Kompletter Stack-Neustart
docker compose -p planbar-kunde1 restart

# Kompletter Stack-Stop
docker compose -p planbar-kunde1 down

# Container-Logs ins Journal
journalctl -u docker.service --since "5 min ago"

# Datenbank-Container neustarten (alle Kunden betroffen)
docker restart db_planbar db_tito
```

### 12.2 Umgebungsvariablen pro Kunde

```bash
# customers/kunde1/.env
FRONTEND_PORT=8081
TITO_PORT=5001
BACKEND_PORT=8001
DOMAIN=kunde1.app.planbar.de

PLANBAR_DB_NAME=kunde1_planbar
TITO_DB_NAME=kunde1_tito

PLANBAR_DB_PASSWORD=<random-64-hex>
TITO_DB_PASSWORD=<random-64-hex>
SECRET_KEY=<random-64-hex>
TITO_API_KEY=<random-32-hex>
TITO_JWT_SECRET=<random-64-hex>
```

### 12.3 Offene Punkte vor Go-Live

- [ ] Secrets aus Git-History entfernen (BFG Repo-Cleaner)
- [ ] `SECRET_KEY` als Required-Feld in `config.py`
- [ ] Production-Guard in `main.py`
- [ ] nginx Security Headers
- [ ] Alembic-Migrationen finalisieren
- [ ] `docker-compose.infra.yaml` erstellen
- [ ] `docker-compose.customer.yaml` erstellen
- [ ] Deployment-Skripte schreiben
- [ ] Caddy-Config für Wildcard-Domain
- [ ] Demo-Seed-Daten erstellen
- [ ] CI/CD-Deploy-Job einrichten
- [ ] Backup-Skript + Cron-Job
- [ ] Docker Resource Limits konfigurieren
- [ ] Ersten Kunden manuell deployen und testen

---

*Erstellt am 01.06.2026 – Basierend auf Codebase-Analyse und Architekturentscheidungen.*
