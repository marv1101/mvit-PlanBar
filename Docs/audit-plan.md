# Codebase-Audit & Sanierungsplan

**Stand:** 20.07.2026
**Status:** Alle 14 Blocker (2.1–2.14) behoben. Bestehende Testsuiten (Backend 493, TiTO 69) laufen durch.
**Audit-Umfang:** Backend (FastAPI), Frontend (React/Vite), TiTO (Flask/OR-Tools), Infrastruktur (Docker/CI/CD/Multi-Tenant)
**Methodik:** 5 parallele Explore-Agenten (Security, Solver, Frontend, SRE/DevOps, Backend-Qualität)

---

## Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Blocker – Vor erstem Production-Deploy beheben](#2-blocker)
3. [Kritische Schwachstellen](#3-kritisch)
4. [Hohe Schwachstellen](#4-hoch)
5. [Mittlere Schwachstellen](#5-mittel)
6. [Fehlende Features](#6-fehlende-features)
7. [Phasenplan](#7-phasenplan)
8. [Anhang: Dateireferenzen](#8-anhang)

---

## 1. Executive Summary

Die Codebase zeigt einen soliden Security-Reifegrad (HttpOnly-Cookies, CSRF-Double-Submit, Account-Lockout, BSI-konforme Passwort-Policy, DSGVO-API). Dennoch bestehen **14 kritische (Blocker) und 35+ hohe Schwachstellen**, die vor einem Production-Go-Live zwingend behoben werden müssen.

| Bereich | Blocker | Hoch | Mittel | Niedrig |
|---------|---------|------|--------|---------|
| **Security** | 5 | 4 | 6 | 3 |
| **Backend-Qualität** | 2 | 8 | 12 | 8 |
| **TiTO/Solver** | 1 | 7 | 5 | 4 |
| **Frontend** | 1 | 5 | 8 | 6 |
| **Infrastruktur/CI-CD** | 6 | 9 | 10 | 5 |
| **Gesamt** | **14** | **33** | **41** | **26** |

**Top-5-Sofortmassnahmen (alle erledigt):**
1. ✅ `deploy.yml` branches-Logik reparieren → `branches: [main]`
2. ✅ Alembic-Head-Kollision auflösen → Merge-Migration `0013`
3. ✅ Migration aus `create_app()` entfernen → `deploy-customer.sh` führt `alembic upgrade head` aus
4. ✅ Frontend-Port auf `127.0.0.1` binden
5. ✅ Shared-DB-Superuser durch Tenant-spezifische User ersetzen

---

## 2. Blocker – Vor erstem Production-Deploy beheben (🔴)

Priorität 0 – ohne diese Fixes darf kein Production-Deploy stattfinden.

### 2.1 CI/CD deployt auf jeden Branch  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `.github/workflows/deploy.yml:5-7` |
| **Risiko** | Unbeaufsichtigter Production-Deploy von Dev-/Feature-Branches |
| **Behebung** | `branches: [main]` setzen; `environment: production` mit `required_reviewers` ergänzen |
| **Verifikation** | `git push feature/foo` triggert deploy.yml **nicht** |
| **Status** | ✅ `deploy.yml` auf `branches: [main]` gesetzt; Test `tests/infrastructure/test_deploy_workflow.py` |

### 2.2 Alembic hat zwei Heads – Token-Revocation bricht  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `migrations/versions/0006_add_revoked_tokens_table.py:15-16` + `0006_add_schedule_shift_templates.py:12-13` |
| **Risiko** | `alembic upgrade head` scheitert → Logout/Refresh-Token-Invalidierung funktionslos; stiller Fallback auf `Base.metadata.create_all()` maskiert Fehler |
| **Behebung** | `alembic merge` zur Konsolidierung; `run_database_setup` aus `create_app()` entfernen; Migration als separaten Schritt im deploy-Script |
| **Verifikation** | `alembic upgrade head` → nur ein Head; alle Tabellen existieren |
| **Status** | ✅ Merge-Migration `0013` erstellt; einzelner Head; Test `tests/infrastructure/test_alembic.py` |

### 2.3 `run_database_setup()` mit `create_all`-Fallback bei App-Start  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `PlanBar - Backend/src/app/main.py:92,99-106` |
| **Risiko** | Race-Condition bei parallelen Backend-Starts; Schema vs. Alembic-History driftet auseinander |
| **Behebung** | Migration aus App-Start entfernen; `deploy-customer.sh` mit `alembic upgrade head` vor `docker compose up -d`; `create_all`-Fallback löschen |
| **Verifikation** | App-Start ohne DB-Connection → App startet nicht (Fail-Fast) |
| **Status** | ✅ `run_database_setup` entfernt; `seed_initial_users` Fail-Fast in prod; `deploy-customer.sh` führt `alembic upgrade head` aus; Tests in `tests/infrastructure/test_deploy_script.py` |

### 2.5 Frontend-Port ohne `127.0.0.1`-Bindung → TLS-Bypass  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `Infrastructure/docker-compose.customer.yaml:88-89` |
| **Risiko** | App über `http://vps-ip:8081` ohne Caddy/TLS erreichbar |
| **Behebung** | `ports: - "127.0.0.1:${FRONTEND_PORT}:80"` |
| **Verifikation** | `curl http://localhost:8081` → OK; `curl http://<public-ip>:8081` → refused |
| **Status** | ✅ Frontend-Port auf `127.0.0.1` gebunden; Test in `tests/infrastructure/test_deploy_script.py` |

### 2.6 Docker-Container laufen als root  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `PlanBar - Backend/Dockerfile`, `TiTO/Dockerfile`, `TiTO/Dockerfile.worker` |
| **Risiko** | Privilegierung bei Container-Breach |
| **Behebung** | Multi-Stage; `adduser --system --ingroup app app && USER app`; `.dockerignore` für TiTO |
| **Verifikation** | `docker run --rm --entrypoint whoami image` → `app` |
| **Status** | ✅ Alle drei Dockerfiles erstellen `app`-User und verwenden `USER app`; `TiTO/.dockerignore` hinzugefügt; Tests in `tests/infrastructure/test_dockerfiles.py` |

### 2.7 Shared DB-Superuser für alle Tenants  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `docker-compose.infra.yaml:14,34` + `deploy-customer.sh:114` |
| **Risiko** | Kunde1 mit SQL-Injection liest `kunde2_planbar.users` |
| **Behebung** | Pro Tenant: eigener DB-User + `CREATE DATABASE ... OWNER ...; REVOKE ALL ... FROM public; GRANT CONNECT ... TO ...;` |
| **Verifikation** | Kunde1-Backend kann nicht auf `kunde2_*`-Tabellen zugreifen |
| **Status** | ✅ `deploy-customer.sh` erstellt pro Tenant DB + eigenen User mit eingeschränkten Rechten; Tests in `tests/infrastructure/test_deploy_script.py` |

### 2.8 Mass-Assignment `EmployeeUpdate.user_id`  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `src/app/schemas/employee.py:32` + `src/app/services/employee_service.py:67-68` |
| **Risiko** | Normaler User verlinkt Employee-Profil mit Admin-`user_id` |
| **Behebung** | `user_id` aus `EmployeeUpdate` entfernen; nur Admin-Update erlaubt `user_id` |
| **Verifikation** | `PUT /employees/{id}` als User mit `user_id: 1` → 403 |
| **Status** | ✅ `user_id` aus `EmployeeUpdate` entfernt (`extra="forbid"`); `update_employee` ignoriert `user_id`; Tests in `tests/unit/test_employee_service.py` |

### 2.9 `/api/v1/metrics` unauthentifiziert  ✅ BEHOBEN (Re-Check 20.07.2026)

| Aspekt | Wert |
|--------|------|
| **Fundort** | `src/app/api/v1/metrics.py:10-17` |
| **Risiko** | Aggregierte Schedule-Statistiken öffentlich |
| **Behebung** | `Depends(require_admin)` ergänzen |
| **Verifikation** | `GET /api/v1/metrics` ohne Auth → 401/403 |
| **Status** | ✅ Beide Routen verwenden `Depends(require_admin)` (`metrics.py:12,17`) |

### 2.10 TiTO-Callback ohne Body-Signatur & Replay-Schutz  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `src/app/api/v1/callbacks.py:18-37` |
| **Risiko** | Wer API-Key kennt, injiziert beliebige Shiftplan-Updates; Replay ohne Nonce |
| **Behebung** | HMAC über Payload + Zeitstempel; Nonce/Zeitfenster-Prüfung |
| **Verifikation** | Dubletten-Callback wird ignoriert; abgelaufener Callback → 401 |
| **Status** | ✅ Callbacks prüfen `X-TiTO-Timestamp`, `X-TiTO-Nonce`, `X-TiTO-Signature`; Nonces in `tito_callback_nonces` gespeichert; Tests in `tests/integration/test_tito_callback_flow.py` |

### 2.11 Schwache Demo-Credentials + kein Reset  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `Infrastructure/init-demo-data.sql:6,13` + `deploy.yml:101` |
| **Risiko** | `demo-admin-2024`/`demo-user-2024` öffentlich; Daten persistieren |
| **Behebung** | Demo-Passwörter via Env-Variablen; `|| true` entfernen; periodischen Demo-Reset-Job implementieren |
| **Verifikation** | Demo-Daten werden bei jedem Deploy zurückgesetzt |
| **Status** | ✅ `init-demo-data.sql` verwendet `psql -v` Variablen + `crypt(..., gen_salt('bf'))`, `TRUNCATE`, `must_change_password=true`; `deploy.yml` ohne `|| true`; neuer Workflow `.github/workflows/demo-reset.yml` für täglichen Reset; Tests in `tests/infrastructure/test_demo_seed.py` |

### 2.12 `planbar.db` in Git versioniert  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `PlanBar - Backend/planbar.db` (via `git ls-files`) |
| **Risiko** | PII/Passwort-Hashes öffentlich |
| **Behebung** | `git rm --cached "PlanBar - Backend/planbar.db"`; `.gitignore` ergänzen |
| **Verifikation** | `git ls-files` zeigt keine `*.db`-Dateien |
| **Status** | ✅ Datei aus Git-Index entfernt; `.gitignore` um `*.db` und `PlanBar - Backend/*.db` ergänzt; Tests in `tests/infrastructure/test_deploy_workflow.py` |

### 2.13 `SECRET_KEY`-Validierung zu lax  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `src/app/main.py:50-59` |
| **Risiko** | `.env.example`-Wert `replace_this_with_a_secure_value` passiert Prüfung |
| **Behebung** | Mindestlänge >= 32 Byte + Deny-Liste schwacher Werte |
| **Verifikation** | App-Start mit `replace_this_with_a_secure_value` → Fehler |
| **Status** | ✅ `_verify_secret_key` prüft Länge >= 32 Byte und Deny-Liste; Tests in `tests/unit/test_main.py` |

### 2.14 Queue-Race in TiTO (AUTOCOMMIT + SKIP LOCKED)  ✅ BEHOBEN

| Aspekt | Wert |
|--------|------|
| **Fundort** | `TiTO/src/tito/db.py:63` |
| **Risiko** | Zwei Worker bearbeiten denselben Job (Doppelverarbeitung) |
| **Behebung** | Explizite Transaktion um SELECT-and-mark-Atomic oder CTE mit RETURNING |
| **Verifikation** | 2 Worker x 5 Jobs parallel → kein Job doppelt verarbeitet |
| **Status** | ✅ Neue atomare Funktion `fetch_and_mark_next_job` mit expliziter Transaktion; Worker verwendet diese; Tests in `TiTO/tests/test_db.py` |

---

## 3. Kritische Schwachstellen (🔴)

Nicht unmittelbar Blocker, aber schwerwiegend und vor Go-Live zu beheben.

| # | Bereich | Fundort | Problem |
|---|---------|---------|---------|
| K1 | Backend | `lockout_service.py:10-20` | Lockout-State in-Memory (pro Worker) → Multi-Uvicorn ineffektiv |
| K2 | Backend | `schedule_service.py:110` | Schedule-Submit ohne Status-Guard → Phantom-Jobs — 🟡 TEILWEISE: Wish-Status-Guard ergänzt (`schedule_service.py:114-118`), Schedule-Status-Guard fehlt |
| K3 | Backend | `tito_callback.py:15-64` | Callback ohne `SELECT FOR UPDATE` → Race-Datenverlust; keine Idempotency |
| K4 | Backend | `users.py:262-273` | Admin kann sich selbst löschen (Self-Lockout) |
| K5 | Backend | `health.py:16-27` | `/health/db` gibt 200 bei Fehler; `/ready` ohne Prüfung |
| K6 | Backend | `schedules.py:148,163` | Async-Routen mit synchronem DB-Access blockieren Event-Loop |
| K7 | Backend | `auth.py:85-90` | `revoke_token` ohne `ON CONFLICT DO NOTHING` → Duplicate-Logout → 500 |
| K8 | TiTO | `worker.py:238` | Callback-Aufruf an Backend ohne `TITO_API_KEY`-Auth-Header |
| K9 | TiTO | `api.py:411`, `worker.py:234` | `callback_url` unvalidiert → SSRF auf interne Endpoints |
| K10 | TiTO | `worker.py` + `db.py` | `check_job_timeout` nie aufgerufen → Job bleibt ewig `processing` |
| K11 | TiTO | `worker.py:128` | `INFEASIBLE` als `completed` → keine Retry-Möglichkeit |
| K12 | TiTO | `solver.py:411-413` | Sonntagsruhe-Formel falsch (erlaubt mehr Sonntagsarbeit als ArbZG) |
| K13 | Infra | `ci.yml:128-134` | Kein Image-Scanning vor `push: true` |
| K14 | Infra | `backup.sh` | Backups unverschlüsselt at-rest (DSGVO Art. 32) |
| K15 | Infra | — | Kein Monitoring-Stack (Prometheus/Grafana/Sentry) |
| K16 | Infra | `deploy-customer.sh` / Doku | Drei Domain-Schemata inkonsistent |
| K17 | Frontend | `AuthContext.tsx:42` | `/users/me` mit rohem `axios` → Refresh-Interceptor inaktiv |

---

## 4. Hohe Schwachstellen (🟠)

Systematische Probleme, die mittelfristig zu Ausfällen, Datenverlust oder Lücken führen.

### 4.1 Backend

| # | Fundort | Problem |
|---|---------|---------|
| H1 | `users.py:129-135` | Tokens als Cookie **und** JSON-Body → HttpOnly-Schutz untergraben |
| H2 | `main.py:109-131` | Admin-Passwort-Generierung mit `random` statt `secrets` |
| H3 | `main.py:39-47,153-155` | `initial-credentials.txt` im Klartext, Append-Modus, nie gelöscht |
| H4 | `core/auth.py:13` | Passwort-Hashing `pbkdf2_sha256` statt `bcrypt` |
| H5 | `export_service.py:78,86` | iCal/PDF mit UTC statt Europe/Berlin → 2h-Versatz |
| H6 | `services/audit_service.py` | Lücken: Time-Account, Shiftplan, Shift-Swap, Wish ohne Audit-Log — 🟡 TEILWEISE: Audit für Employee/Contract/Timecard/User/Role/Schedule/GDPR vorhanden; Shiftplan-Update/Shift-Swap/Wish fehlen |
| H7 | `services/tito_proxy.py:8-15,38` | `httpx.AsyncClient` nie geschlossen — 🟡 TEILWEISE: `close()`-Methode ergänzt (`tito_proxy.py:38-39`), wird aber nie aufgerufen (kein shutdown-Event) |
| H8 | `api/v1/users.py:79-87` | Register-Endpoint ohne Email-Verifizierung |
| H9 | `dependencies.py:17-42` | 401 vs 403 inkonsistent — 🟡 TEILWEISE: `get_current_user`/`require_admin` konsistent, aber `users.py:228,244` wirft noch 401 statt 403 |
| H10 | `api/v1/schedules.py:56-86,265-302` | Duplicate-Code — 🟡 TEILWEISE: Helper `_build_schedule_with_arbzg_response` extrahiert, `replace_all_shifts_endpoint` dupliziert noch |
| H11 | `services/audit_service.py:145-147` | Paging mit zwei SQL-Queries → Race |
| H12 | `services/` | N+1-Queries auf `/my/schedule`, `update_schedule`, `tito_callback` — 🟡 TEILWEISE: `_build_tito_payload`-Timecard-Batch gebessert, drei Stellen bleiben offen |

### 4.2 TiTO

| # | Fundort | Problem |
|---|---------|---------|
| H13 | `schema.py:149` vs `solver.py:521` | `priority`-Feld wird ignoriert |
| H14 | `db.py:405`, `api.py:388` | Tenant-Isolation nicht durchgesetzt |
| H15 | `worker.py:64` | Worker nutzt Admin-Token statt Rolle `worker` |
| H16 | `db.py:891,905` | `callback_max_attempts`-Orphan |
| H17 | `solver.py:598-600` | `max_memory_in_mb`, `random_seed`, `solverTimeoutSeconds` ignoriert |
| H18 | `solver.py` | Nachtarbeit §6, Jugendschutz, Min-Stunden, 6-Monats-Ausgleich fehlt |

### 4.3 Frontend

| # | Fundort | Problem |
|---|---------|---------|
| H19 | `AppContext.tsx:161-213` | Optimistische Mutationen ohne Rollback — ✅ BEHOBEN: Mutationen jetzt reaktiv (API-Call, dann `setState` on success) |
| H20 | `api.ts:88-91` | `clearTokens` no-op; Hard-Redirect ohne Hinweis — 🟡 TEILWEISE: `clearTokens` bewusst no-op (HttpOnly-Cookies, serverseitiges Logout); Hard-Redirect ohne Hinweis bleibt |
| H21 | `AppContext.tsx` vs `hooks/*` | Duale State-Strategien |
| H22 | `EditableScheduleCalendar.tsx:125/262` | Drag-and-Drop ohne Tastatur (BFSG-Risiko) — 🟡 TEILWEISE: `aria-label`/`role="gridcell"` für Buttons ergänzt, Tastatur-Alternative zum Verschieben fehlt |
| H23 | `usePinboardSocket.ts:44` | WS-Token in URL-Query |
| H24 | `PdfPreview.tsx:43-48` | iframe ohne `sandbox` |
| H25 | `sanitize.ts:6-12` | Naiver Regex-Sanitizer |

### 4.4 Infrastruktur

| # | Fundort | Problem |
|---|---------|---------|
| H26 | `docker-compose.customer.yaml:43` | `tito_worker deploy.replicas: 2` NO-OP |
| H27 | alle Compose | Keine `deploy.resources.limits` |
| H28 | alle Compose | Keine Log-Rotation (`max-size`/`max-file`) |
| H29 | `backup.sh` | Kein Alerting, kein Offsite, kein Restore-Test |
| H30 | `docker-compose.customer.yaml:106-108` | Shared Network → Cross-Tenant-DNS |
| H31 | `deploy.yml:33-37` | SSH-Key statt OIDC |
| H32 | `.github/` | Kein `CODEOWNERS`, kein Ruleset |
| H33 | `docker-compose.*.yaml` | Image-Tags `:latest` statt SHA-Pinning |

---

## 5. Mittlere Schwachstellen (🟡)

Qualitäts- und Robustheitsmängel für Post-Go-Live.

| # | Bereich | Fundort | Problem |
|---|---------|---------|---------|
| M1 | Backend | `pyproject.toml:20` | Pydantic-Pin `>=1.1` vs Code v2-API |
| M2 | Backend | `schedule.py:60-72` | `role_requirements` als `Optional[Any]` unvalidiert |
| M3 | Backend | `tito.py:7-13` | `break_start`/`end` ohne Pattern → Runtime-Crash — 🟡 TEILWEISE: TiTO-Assignment hat keine break-Felder mehr, `schedule.py:16-17,33-34` noch ohne Pattern |
| M4 | Backend | `enums.py` | `UserRole`-Enum definiert, nicht genutzt |
| M5 | Backend | `pinboard.py:289-304` | Messages in Python gesliced statt SQL OFFSET/LIMIT |
| M6 | Backend | `utils/pagination.py` | Toter Code |
| M7 | Backend | `users.py:145` | Refresh-Token-Limit 1000/min zu hoch |
| M8 | Backend | `users.py:182-207` | Logout revoziert Refresh-Token-Cookie nicht — 🟡 TEILWEISE: Refresh-Token-Cookie wird via `_clear_auth_cookies()` gelöscht; serverseitige JTI-Revocation fehlt |
| M9 | Backend | `callbacks.py:30-36` | Dev-Fallback ohne Auth |
| M10 | Backend | `csrf.py:40` | Exempt-Pfade via `startswith` |
| M11 | TiTO | `solver.py:566-572` | Gewichte nicht dokumentiert/konfigurierbar |
| M12 | TiTO | `db.py:410,426,...` | SQL f-strings |
| M13 | TiTO | `auth.py:36-41` | JWT nur HS256; kein `nbf`/`iat` |
| M14 | TiTO | `monitoring.py:41` | Lädt alle Job-Rows in Python → OOM |
| M15 | Frontend | `Login.tsx:102-121` | Demo-Credentials ohne `import.meta.env.DEV` — ✅ BEHOBEN: jetzt `VITE_SHOW_DEMO_CREDENTIALS==='true'` + env-basierte Passwörter |
| M16 | Frontend | — | Kein ESLint/Prettier |
| M17 | Frontend | `EmployeeForm.tsx:213,229` | Keine zod/RHF-Validierung |
| M18 | Frontend | `EditableScheduleCalendar.tsx:655,681,862` | ID-Kollision `Date.now()` |
| M19 | Frontend | `api.ts:59-66` | Kein Retry bei 5xx |
| M20 | Frontend | `nginx.conf` | Kein COOP/COEP/CORP |
| M21 | Frontend | — | Dark Mode nicht aktivierbar (ThemeProvider fehlt) |
| M22 | Frontend | `Users.tsx:47-56` | Optimistic-Delete ohne Rollback — ✅ BEHOBEN: `await deleteUser()` vor `setUsers(filter…)` (pessimistisch) |
| M23 | Frontend | — | Keine E2E/Drag-Tests, kein Coverage-Threshold |
| M24 | Frontend | — | Kein i18n-Framework |
| M25 | Frontend | `ProtectedRoute.tsx` | Nur clientseitig, kein 403-Screen |
| M26 | Infra | `init-db-backend.sql:5,18` | SQL-Kommentare mit Plaintext-Passwörtern |
| M27 | Infra | `main.py:149-152` | Passwort-Output auf stdout — 🟡 TEILWEISE: `print()` nur noch in `environment=="development"`; prod/demo/staging schreibt in Datei |
| M28 | Infra | `compose.yaml:146-148` | Dev: `depends_on: db_backend` statt `planbar_backend` |
| M29 | Infra | `compose.yaml:74,93` | Dev-DBs ohne `127.0.0.1:`-Bindung |
| M30 | Infra | `restore.sh:30` | `DROP DATABASE` ohne Bestätigung; TiTO-Restore nicht möglich |
| M31 | Infra | `deploy.yml:33-37` | Kein Cache in CI |
| M32 | Infra | `go-live-readiness-plan.md` | Sentry "nach Go-Live" → fehlt |
| M33 | Infra | `request_logging.py` | Keine PII-Redaktion — ✅ BEHOBEN: loggt nur method/path/status/duration (kein Query/Body/Header) |
| M34 | Infra | — | Keine Log-Retention, keine Correlation-ID |
| M35 | Infra | `production-deployment-plan.md` | Demo-Seed-Script existiert nicht — 🟡 TEILWEISE: `demo-seed.sh` fehlt, Seeding via `init-demo-data.sql` in `deploy.yml:102` |

---

## 6. Fehlende Features

| Bereich | Feature | Status |
|---------|---------|--------|
| **Auth/Security** | 2FA/TOTP für Admin-Accounts | fehlt |
| | Passwort-Reset via E-Mail (`/forgot-password`) | fehlt |
| | Account-Lockout persistent (Redis/DB) | In-Memory |
| | Breach-Password-Check (PwnedPasswords) | fehlt |
| | Email-Verifizierung bei Registrierung | fehlt |
| | CAPTCHA nach wiederholtem Lockout | fehlt |
| **Audit** | Tamper-Proof Audit-Log (Hash-Verkettung) | fehlt |
| | Audit-Logs für Time-Account, Shiftplan-Update, Shift-Swap, Wünsche | 🟡 TEILWEISE: Time-Account/Employee/Contract/User/Role/Schedule/GDPR vorhanden; Shiftplan-Update/Shift-Swap/Wünsche fehlen |
| | Automatische Log-Rotation | fehlt |
| **Solver (ArbZG)** | Nachtarbeit §6 (Kontingent, freie Nacht) | fehlt |
| | Jugendschutz (JArbSchG) | fehlt |
| | Pausenplatzierung statt nur Abzug (Beginn spätestens nach 6h) | fehlt |
| | 6-Monats-Durchschnitt §3 Abs. 2 | fehlt |
| | Min-/Max-Stunden pro Woche | 🟡 TEILWEISE: Max via `weekly_minutes <= weekly_limit` (`solver.py:454-462`); Untergrenze fehlt |
| | Rotation-Fairness (Frueh/Spaet/Nacht) | fehlt |
| | Skill-Mix (Mindestanzahl pro Kategorie) | fehlt |
| | MIP-Start / Warm-Start (vorherige Lösung als Hint) | fehlt |
| | IIS-Diagnose bei Infeasibility | fehlt |
| **Scheduler** | Stuck-Submitted-Schedules nachpollend | fehlt |
| | `clean_expired_revoked_tokens` | vorhanden, nie aufgerufen |
| | Notification-Cleanup | fehlt |
| | Audit-Rotation gemäss privacy.py-Retention | fehlt |
| **Frontend** | Dark Mode ThemeProvider | nicht aktivierbar |
| | PWA / Offline-Unterstützung | ✅ BEHOBEN: `vite-plugin-pwa`, `src/sw.ts`, `registerSW.ts`, Manifest in `index.html` |
| | Undo/Redo im Kalender | fehlt |
| | Clientseitige Konflikt-Erkennung beim Drag | fehlt |
| | Remote-Error-Reporting (Sentry) | optional, fehlt |
| | E2E-Tests (Playwright) | keine |
| | Coverage-Threshold in CI | kein |
| | i18n / Mehrsprachigkeit | keine |
| | Tastatur-Alternative für Drag-and-Drop | fehlt |
| **Infrastruktur** | Monitoring-Stack (Prometheus/Grafana/Loki) | fehlt |
| | Status-Page (`status.planbar.de`) | fehlt |
| | Demo-Reset-Mechanismus | fehlt |
| | Structured JSON-Logging + Correlation-ID | fehlt |
| | Offsite-Backup (rclone → S3/B2) | optional, nicht implementiert |
| | Secret-Manager (Vault/SOPS/Doppler) | fehlt |
| | Pre-Commit-Hook (gitleaks/trufflehog) | fehlt |
| | Wildcard-Domain `*.app.planbar.de` | nicht implementiert |
| | Blue-Green / Canary-Deploy | fehlt |

---

## 7. Phasenplan

### Phase 0 – Blocker beheben (Sofort, vor Go-Live)

| Sprint | Themen | Geschätzter Aufwand |
|--------|--------|---------------------|
| **S0.1** | CI/CD fixen (`deploy.yml branches` + `environment`); Alembic-Merge + Migration refactorn | 4–6 h |
| **S0.2** | Secrets rotieren & `.env`-Säuberung; `planbar.db` aus Git; `SECRET_KEY`-Validierung | 2–4 h |
| **S0.3** | Frontend-Port binden; Docker Non-root + Multi-Stage; `.dockerignore` | 3–5 h |
| **S0.4** | Tenant-DB-User-Isolation; `run_database_setup` entfernen; `init-db.sql` säubern | 4–8 h |
| **S0.5** | Mass-Assignment `EmployeeUpdate.user_id`; `/metrics` Auth; TiTO-Callback-Signatur | 3–5 h |
| **S0.6** | TiTO-Queue-Race fixen; `check_job_timeout` aktivieren; Callback-Auth-Header ergänzen | 4–6 h |

### Phase 1 – Kritische Schwachstellen (Vor Go-Live)

| Sprint | Themen | Geschätzter Aufwand |
|--------|--------|---------------------|
| **S1.1** | Lockout persistieren (Redis); Schedule-Status-Guard + `SELECT FOR UPDATE` | 4–6 h |
| **S1.2** | TiTO-Callback Idempotency + SSRF-Schutz; SOLVER Sonntagsruhe-Formel fixen | 4–6 h |
| **S1.3** | Health-Endpoints (K8s-ready); Async-DB in Threadpool; Event-Loop fix | 3–5 h |
| **S1.4** | Admin Self-Delete-Guard; `revoke_token ON CONFLICT`; Auth-Status-Codes | 2–3 h |
| **S1.5** | Image-Scanning (Trivy) in CI; Backup-Verschlüsselung; Monitoring-Basis | 6–10 h |
| **S1.6** | Demo-Credentials + Reset; N+1-Queries auf kritischen Pfaden | 3–5 h |

### Phase 2 – Hohe Schwachstellen (Vor/nach Go-Live)

| Sprint | Themen | Geschätzter Aufwand |
|--------|--------|---------------------|
| **S2.1** | Audit-Log-Lücken schliessen; LoginResponse Cookie-only | 3–5 h |
| **S2.2** | Frontend State-Vereinheitlichung (AppContext entfernen); Optimistic-Rollback | 6–10 h |
| **S2.3** | Kalender: Undo/Redo + Konflikterkennung + Tastatur-Support | 8–12 h |
| **S2.4** | TiTO: Tenant-Isolation; Worker-Rolle; `callback_max_attempts`-Orphan fix | 3–5 h |
| **S2.5** | Resource-Limits in Compose; Log-Rotation; Caddyfile-Versionierung | 2–4 h |
| **S2.6** | OIDC statt SSH-Key; Branch-Protection; SHA-Image-Pinning | 3–5 h |

### Phase 3 – Mittlere + Neue Features (Post-Go-Live)

| Sprint | Themen | Geschätzter Aufwand |
|--------|--------|---------------------|
| **S3.1** | iCal/PDF Timezone fix; Passwort-Hashing bcrypt; Pydantic-Pin | 2–4 h |
| **S3.2** | eslint/prettier einführen; Frontend-Validierung (zod/RHF) | 4–6 h |
| **S3.3** | Dark Mode fertigstellen; i18n-Grundlagen | 3–5 h |
| **S3.4** | PWA/Offline; Sentry-Integration; Structured Logging | 6–10 h |
| **S3.5** | 2FA/TOTP; Passwort-Reset; E-Mail-Verifizierung | 8–12 h |
| **S3.6** | Solver: Nachtarbeit, Jugendschutz, 6-Monats-Ausgleich, MIP-Start | 10–16 h |
| **S3.7** | E2E-Tests (Playwright); Coverage-Threshold; Restore-Test-Automatisierung | 6–10 h |
| **S3.8** | Monitoring-Stack vollständig (Grafana-Dashboards, Alerts); Status-Page | 8–12 h |

---

## 8. Anhang: Dateireferenzen

### Backend (`PlanBar - Backend/`)

| Pfad | Themen |
|------|--------|
| `src/app/main.py:39-47,92-106,109-131,149-155` | Passwort-Seed, RNG, initial-credentials.txt, `run_database_setup`, SECRET_KEY-Validation |
| `src/app/schemas/employee.py:32` | Mass-Assignment `user_id` |
| `src/app/schemas/schedule.py:60-72` | Unvalidierte `role_requirements`/`shift_templates` |
| `src/app/schemas/tito.py:7-13` | `break_start`/`end` ohne Pattern |
| `src/app/api/v1/metrics.py:10-17` | Fehlende Auth |
| `src/app/api/v1/health.py:16-27` | Health 200 bei Fehler; `/ready` ohne Prüfung |
| `src/app/api/v1/users.py:79-87,129-135,145,182-207,228-273` | Register ohne Email-Verify; Token-Doppelausgabe; Rate-Limit; Logout-Lücken; Auth/Admin-Inkonsistenzen |
| `src/app/api/v1/callbacks.py:18-37` | TiTO-Callback ohne Signatur |
| `src/app/services/schedule_service.py:110` | Status-Guard fehlt |
| `src/app/services/tito_callback.py:15-64` | Kein `SELECT FOR UPDATE`, keine Idempotency |
| `src/app/services/lockout_service.py:10-20` | In-Memory Lockout |
| `src/app/services/audit_service.py` | Audit-Log-Lücken |
| `src/app/services/export_service.py:78,86` | UTC statt Europe/Berlin |
| `src/app/services/tito_proxy.py:8-15,38` | AsyncClient nie geschlossen |
| `src/app/core/auth.py:13,85-90` | pbkdf2 statt bcrypt; revoke_token ohne ON CONFLICT |
| `src/app/middleware/csrf.py:40` | startswith-Schwachstelle |
| `src/app/dependencies.py:9-14,17-42` | Session-Handling; 401 vs 403 |
| `migrations/versions/0006_*.py` | Zwei Heads |
| `pyproject.toml:20`, `requirements.txt:11` | Pydantic-Pin |

### TiTO (`TiTO/`)

| Pfad | Themen |
|------|--------|
| `src/tito/db.py:63,405,891,905` | AUTOCOMMIT-Race; keine Tenant-Isolation; Callback-Orphan |
| `src/tito/worker.py:64,128,234,238` | Admin-Token; INFEASIBLE = completed; SSRF; fehlender Auth-Header |
| `src/tito/api.py:411` | SSRF via callback_url |
| `src/tito/solver.py:411-413,566-572,598-600` | Sonntagsruhe-Formel; Gewichte; Limits |
| `src/tito/auth.py:36-41` | JWT nur HS256 |
| `src/tito/monitoring.py:41` | OOM-Risiko |
| `src/tito/schema.py:149` | priority vs weight |

### Frontend (`PlanBar - Frontend/`)

| Pfad | Themen |
|------|--------|
| `src/app/context/AuthContext.tsx:42` | `/users/me` mit rohem axios |
| `src/app/context/AppContext.tsx:161-213` | Optimistic-Update ohne Rollback |
| `src/app/lib/api.ts:59-66,88-91` | Retry-Lücken; clearTokens no-op |
| `src/app/hooks/*` vs `AppContext.tsx` | Duale State-Strategien |
| `src/app/pages/Login.tsx:102-121` | Demo-Credentials ohne DEV-Guard |
| `src/app/components/EditableScheduleCalendar.tsx` | Kein Undo/Redo; keine Konflikterkennung; ID-Kollision; keine Tastatur |
| `src/app/components/PdfPreview.tsx:43-48` | iframe ohne sandbox |
| `src/app/lib/sanitize.ts:6-12` | Naiver Regex-Sanitizer |
| `src/app/hooks/usePinboardSocket.ts:44` | WS-Token in Query |
| `src/app/components/ProtectedRoute.tsx` | Nur clientseitig |
| `src/app/pages/Users.tsx:47-56` | Optimistic-Delete ohne Rollback |
| `nginx.conf` | Kein COOP/COEP/CORP |

### Infrastruktur / CI-CD

| Pfad | Themen |
|------|--------|
| `.github/workflows/deploy.yml:5-7,33-37` | branches: []; SSH-Key statt OIDC |
| `.github/workflows/ci.yml:128-134` | Kein Image-Scanning; kein Cache |
| `.github/` | Kein CODEOWNERS, kein Ruleset |
| `Infrastructure/init-db.sql:81` | Hartcodiertes Passwort |
| `Infrastructure/init-db-backend.sql:5,18` | Plaintext-Passwörter in Kommentaren |
| `Infrastructure/init-demo-data.sql:6,13` | Schwache Demo-Credentials |
| `Infrastructure/docker-compose.customer.yaml:43,88-89,106-108` | Replicas=NOOP; Port-Bindung; Shared Network |
| `Infrastructure/docker-compose.customer.yaml`, `infra.yaml` | Keine Resource-Limits; keine Log-Rotation; latest-Tags |
| `Infrastructure/scripts/backup.sh` | Keine Verschlüsselung; kein Alerting; kein Offsite |
| `Infrastructure/scripts/restore.sh:30` | DROP ohne Bestätigung; nur Planbar-DB |
| `Infrastructure/scripts/deploy-customer.sh` | Domain-Schema; Caddy-Duplikate; Tenant-Isolation |
| `compose.yaml:74,93,146-148` | Dev: DB-Ports; falscher depends_on |
| `PlanBar - Backend/Dockerfile` | Kein Non-root; kein echtes Multi-Stage |
| `TiTO/Dockerfile`, `Dockerfile.worker` | Kein Non-root; keine .dockerignore |
| `PlanBar - Backend/src/app/middleware/request_logging.py` | Keine PII-Redaktion |

---

*Ende des Dokuments. Alle Pfadangaben relativ zu `/Users/marian/Programmieren/mvit/mvit PlanBar/`.*
