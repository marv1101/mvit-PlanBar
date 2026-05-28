# Go-Live Readiness Plan

## Übersicht

Dieser Plan beschreibt alle notwendigen Schritte, um die PlanBar/TiTO-Applikation production-ready zu machen.
Die Priorisierung folgt dem Risiko für den Produktivbetrieb: **Security > Robustheit > Qualität > Komfort**.

**Stand:** 28.05.2026 (Update: 0.3, 0.4, 3.1, 3.2, 4.1, 6.2, 7.2)  
**Branches:** `bugfix-tito-callback` (HEAD), `dev`, `main`  
**Codebase:** ~50 identifizierte Themen (5 kritisch, 1 hoch, 13 mittel, 27 niedrig)

---

## Phase 0 — Security Cleanup & Secrets Management

> **Warum zuerst:** Kompromittierte Credentials und offene CORS sind die häufigste Einfallquelle für Angriffe.  
> **Aufwand:** ~4-6 Stunden  
> **Riskio bei Nichtumsetzung:** Sehr hoch

### 0.1 Secrets aus git entfernen & `.gitignore` fixen

**Status:** erl
**Dateien:**
- `Infrastructure/.env` — committed mit DB-Passwörtern, JWT-Secret, API-Key
- `PlanBar - Backend/.env` — committed mit `change_me`-Defaults

**Aufgaben:**
1. `git rm --cached Infrastructure/.env`
2. `git rm --cached "PlanBar - Backend/.env"`
3. `git commit -m "chore: remove committed .env files"`
4. `.gitignore` prüfen und ggf. ergänzen:
   ```
   # .env files
   **/.env
   **/.env.*
   !.env.example
   ```
5. Prüfen, ob `Infrastructure/.env` bereits in `.gitignore` ist (Zeile 2) — ja, aber `PlanBar - Backend/.env` ist auch drin (Zeile 16). Trotzdem die Dateien aus git history entfernen (BFG Repo-Cleaner oder `git filter-branch`).

**Verifikation:** `git status` zeigt keine `.env`-Dateien mehr an.

### 0.2 `.env.example` für alle Komponenten anlegen

**Status:** erl  
**Dateien:**
- `PlanBar - Backend/.env.example` — neu erstellen
- `TiTO/.env.example` — neu erstellen
- `Infrastructure/.env.example` — neu erstellen

**Aufgaben:**
1. Backend `.env.example`:
   ```
   DATABASE_URL=sqlite:///./planbar.db
   SECRET_KEY=<generate-with: openssl rand -hex 32>
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=15
   REFRESH_TOKEN_EXPIRE_DAYS=7
   TITO_API_URL=http://tito:5001
   BACKEND_CALLBACK_URL=http://planbar_backend:8000
   TITO_API_KEY=
   ```
2. Infrastructure `.env.example` analog
3. TiTO `.env.example` analog

### 0.3 Hardcodierte Passwörter aus `main.py` entfernen

**Status:** ✅ Erledigt  
**Datei:** `PlanBar - Backend/src/app/main.py:65-97`

**Problem:** `seed_initial_users()` nutzte `password="Admin@123"` und `password="User@123"`.

**Lösung:**
- Ersetzt durch `uuid.uuid4().hex[:12]` — zufälliges 12-Zeichen-Initialpasswort pro Backend-Start
- Passwörter werden via `logger.info()` auf der Backend-Konsole ausgegeben
- `must_change_password` (war bereits `True` via `create_user()`) zwingt User zu Passwort-Änderung beim ersten Login
- Kein Production-Guard — UUID-Passwörter sind sicher genug, seeding ist idempotent (nur wenn User nicht existiert)

```python
admin_password = uuid.uuid4().hex[:12]
create_user(db, UserCreate(..., password=admin_password), role="admin")
logger.info("Initial-Passwort fuer admin@mphion.de: %s", admin_password)
```

**Verifikation:** `grep -r "Admin@123\|User@123" src/` findet nichts. Backend-Konsole zeigt Initialpasswörter beim Start.

### 0.4 Demo-Credentials aus Login.tsx entfernen

**Status:** ✅ Erledigt  
**Datei:** `PlanBar - Frontend/src/app/pages/Login.tsx:102-113`

**Problem:** Die Login-Seite zeigte hardcodierte Demo-Zugangsdaten im UI an (admin@mphion.de / Admin@123).

**Lösung:**
- Demo-Credentials-Block in `{import.meta.env.VITE_SHOW_DEMO_CREDENTIALS === 'true' && (...)}` gewrapped
- Passwörter zusätzlich aus `VITE_DEMO_ADMIN_PASSWORD` / `VITE_DEMO_USER_PASSWORD` Env-Vars gelesen (mit Fallback)
- `.env` (Default): `VITE_SHOW_DEMO_CREDENTIALS=false`, `.env.development`: `VITE_SHOW_DEMO_CREDENTIALS=true`

```tsx
{import.meta.env.VITE_SHOW_DEMO_CREDENTIALS === 'true' && (
  <div className="mt-6 space-y-2 text-sm text-gray-600">
    <p className="text-center font-medium">Demo-Zugangsdaten:</p>
    <div className="bg-gray-50 p-3 rounded-md space-y-1">
      <p><strong>Administrator:</strong></p>
      <p className="text-xs">Email: admin@mphion.de</p>
      <p className="text-xs">Passwort: {import.meta.env.VITE_DEMO_ADMIN_PASSWORD || 'Admin@123'}</p>
    </div>
    ...
  </div>
)}
```

**Verifikation:** Production-Build zeigt keine Credentials mehr. Dev-Build zeigt sie weiterhin.

### 0.5 CORS konfigurieren

**Status:** ✅ Erledigt  
**Datei:** `PlanBar - Backend/src/app/main.py:26-29`

**Problem:** `allow_origins=["*"]` mit `allow_credentials=True` — ungültige Kombination laut CORS-Spezifikation und unsicher.

**Lösung:**
```python
allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["http://localhost:5173"],
```
In `config.py` ergänzen:
```python
cors_origins: str = "http://localhost:5173,http://localhost:3000"
```
In Production via Env: `CORS_ORIGINS=https://app.planbar.de`

**Verifikation:** OPTIONS-Requests von nicht-erlaubten Origins werden abgewiesen.

### 0.6 Default `SECRET_KEY` entfernen

**Status:** ❌ Offen  
**Datei:** `PlanBar - Backend/src/app/config.py:15`

**Problem:** `secret_key: str = Field("change-me-in-production")` — in Production wird der Key schnell vergessen.

**Lösung:**
```python
secret_key: str = Field(...)  # kein Default
# + Validierung beim App-Start:
if settings.secret_key == "change-me-in-production":
    raise RuntimeError("SECRET_KEY must be changed in production")
```

### 0.7 Rate-Limiting auf Login-Endpoint

**Status:** ✅ Erledigt  
**Datei:** `PlanBar - Backend/src/app/api/v1/users.py:39-51`

**Problem:** Kein Schutz vor Brute-Force-Angriffen.

**Lösung:**
- `slowapi` (FastAPI-kompatibel) oder manuelles In-Memory-Limiting:
  ```python
  from slowapi import Limiter
  from slowapi.util import get_remote_address

  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter

  @router.post("/login")
  @limiter.limit("5/minute")
  async def login(...):
  ```
- Oder Redis-basiert für Production (mehrere Backend-Instanzen)

**Verifikation:** 6+ Login-Versuche pro Minute → HTTP 429.

### 0.8 Admin-Rollen-Check auf allen Admin-Endpoints

**Status:** ✅ Erledigt  
**Dateien:**
- `PlanBar - Backend/src/app/api/v1/roles.py:34-36`
- `PlanBar - Backend/src/app/api/v1/schedules.py:32-38`
- Weitere Endpoints prüfen

**Problem:** Viele Endpoints nutzen nur `get_current_user` statt `require_admin`.

**Lösung:**
```python
# In dependencies.py
async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# In endpoints:
@router.delete("/{id}")
async def delete_role(id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
```

**Endpoints mit fehlendem Admin-Check:**
- `roles.py`: POST, PUT, DELETE
- `schedules.py`: POST, PUT, DELETE (submission to TiTO)
- `employees.py`: DELETE
- `users.py`: GET (alle User), DELETE

**Verifikation:** Nicht-Admin-User erhalten 403 auf Admin-Endpoints.

### 0.9 JWT-Tokens in HttpOnly-Cookies statt localStorage

**Status:** ✅ Erledigt  
**Dateien:**
- `PlanBar - Backend/src/app/dependencies.py` — `get_current_user` liest Token aus Cookie oder Authorization-Header
- `PlanBar - Backend/src/app/api/v1/users.py` — Login/Refresh setzen HttpOnly-Cookies, `/logout` löscht sie
- `PlanBar - Backend/src/app/schemas/user.py` — `TokenRefreshRequest.refresh_token` optional
- `PlanBar - Frontend/src/app/lib/auth.ts` — localStorage-Funktionen durch No-Ops ersetzt
- `PlanBar - Frontend/src/app/lib/api.ts` — `withCredentials: true`, kein Bearer-Header mehr, Refresh cookie-basiert
- `PlanBar - Frontend/src/app/context/AuthContext.tsx` — initialer `/users/me`-Call via raw axios (kein Interceptor-Loop), Logout ruft `/users/logout`
- `PlanBar - Backend/tests/conftest.py` — `DATABASE_URL`-Override vor App-Imports

**Problem:** localStorage ist anfällig für XSS. HttpOnly-Cookies sind nicht per JavaScript lesbar.

**Lösung:**
- Backend: Set-Cookie-Header bei Login/Refresh:
  ```python
  response.set_cookie(
      key="access_token",
      value=access_token,
      httponly=True,
      secure=False,     # true in Production (HTTPS)
      samesite="lax",
      max_age=900       # 15 Minuten
  )
  ```
- Frontend: `withCredentials: true` im Axios-Client, localStorage-Logik entfernt
- Logout: Cookie löschen via `/users/logout`-Endpoint

**Verifikation:** Token ist in devtools (Application > Cookies) sichtbar, nicht in localStorage.

---

## Phase 1 — Error Handling & Robustheit

> **Warum:** Silent Failures führen zu Datenverlust und schwer diagnostizierbaren Bugs.  
> **Aufwand:** ~6-8 Stunden  
> **Risiko bei Nichtumsetzung:** Hoch

### 1.1 Leere `catch {}` Blöcke im Frontend ersetzen

**Status:** ✅ Erledigt  
**Dateien:**
- `PlanBar - Frontend/src/app/context/AuthContext.tsx` — `.catch(() => {})` → console.error in DEV, Login-Fehler → toast, Passwort-Fehler → toast, Logout-Fehler → console.error
- `PlanBar - Frontend/src/app/lib/mappers.ts` — working_hours_json parse → `console.error`
- `PlanBar - Frontend/src/app/context/AppContext.tsx` — bereits mit toast.error (keine Änderung nötig)

**Verifikation:** Fehler werden im UI angezeigt und/oder in der Console geloggt.

### 1.2 Exception-Details im Backend loggen

**Status:** ✅ Erledigt  
**Dateien:**
- `PlanBar - Backend/src/app/services/schedule_service.py` — `logger.exception()` in `submit_schedule_to_tito` und `retry_schedule`
- `PlanBar - Backend/src/app/services/tito_callback.py` — `logger.warning` → `logger.exception` in `_extract_employee_id`

**Verifikation:** Fehler erscheinen mit Stacktrace im Log. Tests weiterhin grün (150/150).

### 1.3 Axios-Timeout und Retry konfigurieren

**Status:** ✅ Erledigt (zusammen mit 1.4)  
**Datei:** `PlanBar - Frontend/src/app/lib/api.ts`

**Lösung:**
- `timeout: 15000` in axios.create()
- Retry-Interceptor: bei Netzwerkfehler/Timeout bis zu 3 Versuche mit exponentiell ansteigendem Delay (1s, 2s, 3s)

**Verifikation:** Bei Timeout/Netzwerkfehler wird 3x retried, dann Fehler angezeigt.

### 1.4 Token-Refresh-Interceptor verbessern

**Status:** ✅ Erledigt (zusammen mit 1.3)  
**Datei:** `PlanBar - Frontend/src/app/lib/api.ts`

**Lösung:**
- Promise-basierte `failedQueue` mit `resolve`/`reject` statt einfachem Callback-Array
- `processQueue(error, token)` — bei Refresh-Erfolg resolved, bei Fehler rejected
- Parallel-Requests werden korrekt gewartet und bei Refresh-Fehler abgewiesen (hängen nicht mehr)

**Verifikation:** 5 parallele Requests mit abgelaufenem Token → nur 1 Refresh-Request; bei Refresh-Fehler werden alle queued Requests rejected.

### 1.5 Polling-Interval sauber cleaen

**Status:** ✅ Erledigt  
**Datei:** `PlanBar - Frontend/src/app/pages/Schedule.tsx:77-106`

**Problem:** Interval wurde bei Dependency-Wechsel nicht gestoppt, potenzielles setState auf unmounted Component.

**Lösung:**
- `pollRef`/`stopPolling` entfernt (überflüssig geworden)
- `useEffect` für Polling returned direkt `clearInterval(interval)` als cleanup
- Interval wird bei Unmount, bei Status- oder ID-Wechsel sauber gestoppt

**Verifikation:** Navigate away → kein `setState`-Warning in Console; cleanup läuft bei jedem Dependency-Wechsel.

### 1.6 DB Connection-Pooling konfigurieren

**Status:** ✅ Erledigt  
**Datei:** `PlanBar - Backend/src/app/db/database.py`

**Lösung:**
```python
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
)
```

**Verifikation:** Unter Last werden Connections aus dem Pool wiederverwendet. Tests weiterhin grün (150/150).

### 1.7 Request-Body-Größenlimit

**Status:** ✅ Erledigt  
**Dateien:**
- `PlanBar - Backend/src/app/middleware/request_size_limit.py` — neu erstellt
- `PlanBar - Backend/src/app/main.py` — Middleware registriert

**Lösung:**
```python
# Neue Middleware: prüft Content-Length-Header vor Body-Verarbeitung
app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)
```

**Verifikation:** Request > 10 MB → HTTP 413. Tests weiterhin grün (150/150).

---

## Phase 2 — CI/CD & Code Quality

> **Warum:** Ohne automatisierte Tests und Linting schleicht sich Qualitätsverlust ein.  
> **Aufwand:** ~4-6 Stunden initial, ~2h/Woche Betrieb  
> **Risiko bei Nichtumsetzung:** Mittel

### 2.1 GitHub Actions für Tests

**Status:** ✅ Erledigt  
**Ziel:** `.github/workflows/ci.yml`

**Aufgaben:**
```yaml
name: CI
on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: planbar_test
          POSTGRES_USER: planbar
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r "PlanBar - Backend/requirements.txt"
      - run: pip install pytest pytest-cov
      - run: pytest
        working-directory: "PlanBar - Backend"
        env:
          DATABASE_URL: postgresql://planbar:test@localhost/planbar_test

  tito:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r TiTO/requirements.txt
      - run: pytest
        working-directory: TiTO

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
        working-directory: "PlanBar - Frontend"
      - run: npm run build
        working-directory: "PlanBar - Frontend"
      # Optional: npm test wenn Tests vorhanden
```

### 2.2 ESLint + Prettier (Frontend)

**Status:** ❌ Offen

**Aufgaben:**
```bash
cd "PlanBar - Frontend"
pnpm add -D eslint @eslint/js typescript-eslint prettier eslint-config-prettier
```

`eslint.config.js`:
```javascript
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
    eslint.configs.recommended,
    ...tseslint.configs.recommended,
    {
        rules: {
            '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
            '@typescript-eslint/no-explicit-any': 'warn',
        },
    },
);
```

`package.json` Scripts:
```json
{
    "lint": "eslint src/",
    "format": "prettier --write src/",
    "typecheck": "tsc --noEmit"
}
```

### 2.3 ruff + mypy (Backend)

**Status:** ❌ Offen

**Aufgaben:**

`pyproject.toml`:
```toml
[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "PL"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["PLR2004"]

[tool.mypy]
strict = true
ignore_missing_imports = true
warn_unused_ignores = true
```

Scripts:
```bash
ruff check src/
ruff format --check src/
mypy src/
```

### 2.4 TypeScript-Strict-Mode aktivieren

**Status:** ❌ Offen  
**Problem:** Kein `tsconfig.json` vorhanden, Vite nutzt Defaults (lax).

**Lösung:**
```json
{
    "compilerOptions": {
        "target": "ES2020",
        "lib": ["ES2020", "DOM", "DOM.Iterable"],
        "module": "ESNext",
        "moduleResolution": "bundler",
        "strict": true,
        "noUncheckedIndexedAccess": true,
        "noImplicitReturns": true,
        "noFallthroughCasesInSwitch": true,
        "skipLibCheck": true,
        "jsx": "react-jsx",
        "baseUrl": ".",
        "paths": { "@/*": ["./src/*"] }
    },
    "include": ["src"]
}
```

- `tsconfig.node.json` für Vite-Config
- `vite.config.ts` anpassen: `resolve: { alias: { '@': '/src' } }`

### 2.5 Frontend-Tests aufsetzen

**Status:** ❌ Offen

**Setup:**
```bash
pnpm add -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

`vite.config.ts`:
```typescript
test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
}
```

**Erste Test-Suite:** `src/app/components/__tests__/Login.test.tsx`
- Rendert Login-Formular
- Submit mit leeren Feldern → Validierung
- Submit mit gültigen Credentials → `onLogin` wird gecalled

**Ziel:** Kritische User-Flows (Login, Employee-CRUD, Schedule-Ansicht) abdecken.

---

## Phase 3 — Performance & Bundle-Optimierung

> **Warum:** Langsame Ladezeiten und ruckelnde UI schrecken User ab.  
> **Aufwand:** ~3-4 Stunden  
> **Risiko bei Nichtumsetzung:** Mittel

### 3.1 Code-Splitting mit `React.lazy()`

**Status:** ✅ Erledigt  
**Datei:** `PlanBar - Frontend/src/app/routes.tsx`, `FullPageSpinner.tsx` (neu)

**Lösung:**
- Alle Page-Imports (`Dashboard`, `Employees`, `Schedule`, `Requests`, `Roles`, `Users`, `EmployeeView`, `Home`) auf `lazy(() => import(...))` umgestellt
- `FullPageSpinner`-Komponente als Suspense-Fallback erstellt (zentrierter `Loader2`-Spinner)
- `Layout` und `ProtectedRoute` bleiben statisch (werden sofort benötigt)

```typescript
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Employees = lazy(() => import('./pages/Employees'));
// ...

function LazyPage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<FullPageSpinner />}>{children}</Suspense>;
}
```

**Verifikation:** `pnpm run build` erzeugt separate Chunks pro Page (z. B. `Schedule-LUMRjoIi.js` 115 kB, `Dashboard-sKOwS4JJ.js` 9 kB).

### 3.2 Unused Packages entfernen

**Status:** ✅ Erledigt  
**Datei:** `PlanBar - Frontend/package.json`

**Entfernt (7 Pakete):**
- `@mui/material`, `@mui/icons-material`, `@emotion/react`, `@emotion/styled` — MUI-Stack (nicht importiert)
- `react-slick` — nicht importiert
- `canvas-confetti` — nicht importiert
- `react-responsive-masonry` — nicht importiert

**Behalten (werden von shadcn/ui-Komponenten verwendet):**
- `embla-carousel-react` → `carousel.tsx`
- `input-otp` → `input-otp.tsx`
- `vaul` → `drawer.tsx`

```bash
pnpm remove @mui/material @mui/icons-material @emotion/react @emotion/styled react-slick canvas-confetti react-responsive-masonry
```

**Verifikation:** `pnpm run build` läuft ohne Fehler durch. Main-Bundle reduziert (371 kB gzip: 120 kB).

### 3.3 Unused UI-Komponenten aufräumen

**Status:** Abgeschlossen  
**Verzeichnis:** `PlanBar - Frontend/src/app/components/ui/`

**Problem:** ~20 von ~45 shadcn/ui-Komponenten werden vermutlich nicht genutzt.

**Vorgehen:**
1. Pro Komponente prüfen: `grep -r "from.*ui/<komponente>" src/`
2. Unbenutzte löschen (carousel, chart, calendar, drawer, hover-card, menubar, navigation-menu, pagination, resizable, scroll-area, sheet, sidebar, slider, toggle, tooltip)

**Verifikation:** `npm run build` ohne Fehler.

### 3.4 React.memo + useMemo im Calendar

**Status:** ❌ Offen  
**Datei:** `PlanBar - Frontend/src/app/components/EditableScheduleCalendar.tsx` (854 Zeilen)

**Problem:** Der Kalender rendert bei jeder Interaktion alle Zellen neu.

**Lösung:**
```typescript
const DayColumn = React.memo(({ day, shifts, employees, ... }: DayColumnProps) => {
    // ...
});

// useMemo für berechnete Werte:
const hours = useMemo(() => Array.from({ length: 24 }, (_, i) => i), []);
const days = useMemo(() => getDaysInWeek(weekStart), [weekStart]);
```

**Grobe Analyse der Re-Render-Ketten:**
- `DayColumn` wird bei jedem `selectedDate`-Change neu gerendert → `React.memo` hilft
- `ShiftBar` bei jedem Drag/Hover → Callback-Stabilisierung mit `useCallback`

### 3.5 Bundle-Analyse

**Status:** ❌ Offen

**Aufgaben:**
```bash
pnpm add -D vite-bundle-analyzer
```

`vite.config.ts`:
```typescript
import { bundleAnalyzer } from 'vite-bundle-analyzer';
export default defineConfig({
    plugins: [react(), bundleAnalyzer()],
});
```

`npm run build -- --analyze` → Report zeigen große Dependencies auf.

### 3.6 Pagination für Employee/Schedule-Listen

**Status:** ❌ Offen  
**Problem:** `AppContext` lädt alle Daten auf einmal. Bei 100+ Mitarbeitern oder mehrwöchigen Plänen wird das langsam.

**Lösung:**
- Backend: Bereits `pagination.py` vorhanden, aber ungenutzt → in Endpoints einbauen
- `GET /api/v1/employees?page=1&page_size=25`
- `GET /api/v1/schedules?page=1&page_size=10`
- Frontend: Scroll-basiertes Laden oder "Load More"-Button

---

## Phase 4 — Accessibility & UX

> **Warum:** Barrierefreiheit ist nicht nur gesetzlich relevant (BITV/BGG), sondern verbessert UX für alle.  
> **Aufwand:** ~4-6 Stunden  
> **Risiko bei Nichtumsetzung:** Mittel (rechtlich), Niedrig (funktional)

### 4.1 ARIA-Attribute auf interaktiven Elementen

**Status:** ✅ Erledigt  
**Dateien:** `EditableScheduleCalendar.tsx`, `EmployeeForm.tsx`, `Layout.tsx`, `Schedule.tsx`, `Requests.tsx`, `Employees.tsx`, `Roles.tsx`, `Users.tsx`

**Umgesetzt:**

| Komponente | Attribute | Datei |
|---|---|---|
| `ShiftBar` Edit/Delete | `aria-label="Schicht {name} {zeit} bearbeiten/löschen"` | `EditableScheduleCalendar.tsx:156,162` |
| `DayColumn` | `role="gridcell" aria-label="{Datum}"` | `EditableScheduleCalendar.tsx:253` |
| `EmployeeForm` Farb-Swatches | `role="radio" aria-checked aria-label="Farbe {hex}"` + Container `role="radiogroup"` | `EmployeeForm.tsx:159,167` |
| Navigation | `aria-current="page"` auf aktivem Link | `Layout.tsx:80` |
| Icon-Buttons (10x) | `aria-label="Bearbeiten/Löschen/Exportieren/Kopieren"` | alle Pages |

### 4.2 Keyboard-Support für den Kalender

**Status:** ❌ Offen  
**Datei:** `EditableScheduleCalendar.tsx`

**Problem:** Drag&Drop ist Mouse-only.

**Lösung (Minimum):**
- Tab-Reihenfolge durch die Schichten
- Enter/Space zum Öffnen des Edit-Dialogs
- Pfeiltasten zum Navigieren zwischen Schichten
- Oder: "Schicht verschieben"-Dialog mit Datum/Zeit-Auswahl als Alternative zu DnD

```typescript
// Key-Handler auf ShiftBar:
<div
    role="button"
    tabIndex={0}
    aria-label={`Schicht: ${shift.employeeId} ${shift.startTime}-${shift.endTime}`}
    onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onEdit(shift);
        }
        if (e.key === 'Delete') {
            e.preventDefault();
            onDelete(shift);
        }
    }}
>
```

### 4.3 Focus-Management für Dialoge

**Status:** ❌ Offen

**Problem:** Beim Öffnen von Modals/Sheets wird der Focus nicht ins Modal gesetzt, beim Schließen nicht zurück zum Trigger.

**Lösung:**
- shadcn/ui `Dialog` hat `autoFocus` bereits teilweise integriert
- Prüfen: `focus-trap`-Package oder `@radix-ui/react-focus-scope`
- Nach Dialog-Schließen: `triggerRef.current?.focus()`

### 4.4 Alert-Dialog statt `confirm()`

**Status:** ❌ Offen  
**Problem:** Native `confirm('...')`-Dialoge sind nicht stylbar und nicht barrierefrei.

**Lösung:**
```tsx
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';

<AlertDialog>
    <AlertDialogTrigger asChild>
        <Button variant="destructive">Löschen</Button>
    </AlertDialogTrigger>
    <AlertDialogContent>
        <AlertDialogHeader>
            <AlertDialogTitle>Mitarbeiter löschen?</AlertDialogTitle>
            <AlertDialogDescription>
                Diese Aktion kann nicht rückgängig gemacht werden.
            </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
            <AlertDialogCancel>Abbrechen</AlertDialogCancel>
            <AlertDialogAction onClick={onConfirm}>Löschen</AlertDialogAction>
        </AlertDialogFooter>
    </AlertDialogContent>
</AlertDialog>
```

**Dateien mit `confirm()`:**
- `Employees.tsx`
- `Requests.tsx`
- `Roles.tsx`
- `Schedule.tsx`

### 4.5 Skeleton-Screens einbauen

**Status:** ❌ Offen  
**Problem:** `skeleton.tsx` existiert, wird aber nicht verwendet. Stattdessen `Loader2`-Spinner.

**Lösung:**
```tsx
// Statt:
{loading && <Loader2 className="animate-spin" />}

// Besser:
{loading && (
    <div className="space-y-3">
        <Skeleton className="h-8 w-[250px]" />
        <Skeleton className="h-4 w-[200px]" />
        <Skeleton className="h-12 w-full" />
    </div>
)}
```

### 4.6 `'#gray'`-Fallback fixen

**Status:** ❌ Offen  
**Datei:** `PlanBar - Frontend/src/app/pages/Requests.tsx:73`

```typescript
// Falsch:
return employee?.color || '#gray';

// Richtig:
const FALLBACK_COLOR = '#6b7280'; // tailwind gray-500
return employee?.color || FALLBACK_COLOR;
```

---

## Phase 5 — Infrastruktur & Deployment

> **Warum:** Ohne saubere Infrastruktur ist Deployment fehleranfällig und nicht reproduzierbar.  
> **Aufwand:** ~4-6 Stunden  
> **Risiko bei Nichtumsetzung:** Mittel

### 5.1 Alembic-Migrationen finalisieren

**Status:** ⚠️ Teilweise vorhanden  
**Dateien:**
- `alembic.ini` — existiert, aber hardcodiert auf SQLite
- `migrations/versions/0001_initial.py` — existiert (laut Plan)
- `main.py` nutzt `Base.metadata.create_all()` — unsicher für Production

**Aufgaben:**
1. `alembic.ini` auf Env-Variable umstellen:
   ```
   sqlalchemy.url = %(DATABASE_URL)s
   ```
2. Prüfen, ob `migrations/env.py` korrekt die Models importiert
3. Migration erstellen: `alembic revision --autogenerate -m "initial"`
4. `main.py`: `create_all()` durch `alembic upgrade head` ersetzen (oder in Startup prüfen)

**Verifikation:** Migration läuft auf frischer PostgreSQL ohne Fehler.

### 5.2 Dockerfile-Pfadkorrektur (Backend)

**Status:** ❌ Offen  
**Datei:** `PlanBar - Backend/Dockerfile`

**Problem:** `COPY src/app ./app` → würde zu `/app/app/` führen.

**Lösung prüfen:**
```dockerfile
# Aktuell vermutlich:
COPY src/app /app

# Nötig:
COPY src/app /app/app
# Oder im WORKDIR:
WORKDIR /app
COPY src/app .
```
Je nachdem, wie der Pfad in `CMD` referenziert wird (`app.main:app` vs `main:app`).

### 5.3 compose.yaml finalisieren

**Status:** ⚠️ Prüfbar  
**Datei:** `Infrastructure/compose.yaml`

**Checkliste:**
- `db_backend` Service: `init-db-backend.sql` wird gemountet? (laut Analyse nicht)
- Healthchecks für alle Services
- Restart-Policy: `unless-stopped` oder `always`
- Resource-Limits (memory, cpu)
- Logging-Konfiguration (json-file mit Rotation)
- Networks korrekt konfiguriert

### 5.4 nginx Security Headers

**Status:** ❌ Offen  
**Datei:** `PlanBar - Frontend/nginx.conf`

**Lösung:**
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "0" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### 5.5 Healthcheck-Aggregation

**Status:** ❌ Offen  
**Datei:** `PlanBar - Backend/src/app/api/v1/health.py`

**Ziel:** Ein aggregierter `/health`-Endpoint:
```python
@router.get("/health")
async def health():
    db_ok = await check_db()
    tito_ok = await check_tito()
    return {
        "status": "healthy" if (db_ok and tito_ok) else "degraded",
        "checks": {
            "database": "healthy" if db_ok else "unhealthy",
            "tito": "healthy" if tito_ok else "unhealthy",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
```

### 5.6 Structured Logging (JSON)

**Status:** ❌ Offen  
**Datei:** `PlanBar - Backend/src/app/core/logging.py`

**Lösung:**
```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

Oder einfacher: `python-json-logger`:
```python
from pythonjsonlogger import jsonlogger

handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
)
handler.setFormatter(formatter)
```

### 5.7 Environment-Trennung dev/staging/prod

**Status:** ❌ Offen

**Lösung:**
- `.env.development` — lokale Entwicklung
- `.env.staging` — Staging-Umgebung
- `.env.production` — Production (nie in git)

Start-Scripte:
```bash
# development
ENVIRONMENT=development uvicorn app.main:app --reload

# production
ENVIRONMENT=production gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

Im Code:
```python
settings.environment = os.getenv("ENVIRONMENT", "development")
if settings.environment == "production":
    # Strengere Checks
    assert settings.secret_key not in ("change-me-in-production", ""), "..."
```

---

## Phase 6 — Accessibility (Detail) & i18n

> **Warum:** Rechtliche Anforderungen (BITV 2.0 ab 2025 für öffentliche Stellen) und internationale Kunden.  
> **Aufwand:** ~8-12 Stunden  
> **Risiko bei Nichtumsetzung:** Niedrig (funktional), aber strategisch wichtig

### 6.1 i18n-Grundlage schaffen

**Status:** ❌ Offen

**Vorschlag:** `react-i18next` (leichtgewichtig, gut mit React kombinierbar)

```bash
pnpm add react-i18next i18next
```

**Struktur:**
```
src/app/locales/
├── de/
│   ├── common.json
│   ├── employees.json
│   ├── schedule.json
│   └── ...
└── en/
    └── ...
```

**Migration:** Strings nach und nach aus den Komponenten in JSON-Dateien extrahieren.
- **Prio 1:** Alle User-facing Strings (Button-Labels, Fehlermeldungen, Dialog-Texte)
- **Prio 2:** Formular-Validierung
- **Prio 3:** Dashboard-Beschreibungen

**Mindestens für Go-Live:** i18n-Infrastruktur + deutsche Locale (Bestand). Englisch kann später folgen.

### 6.2 Responsive Design für Kalender

**Status:** ✅ Erledigt  
**Dateien:** `EditableScheduleCalendar.tsx`, `ScheduleCalendar.tsx`, `ShiftListView.tsx` (neu), `useMediaQuery.ts` (neu)

**Umgesetzt:**
- `react-dnd-touch-backend` installiert, `HTML5Backend` durch `TouchBackend` mit `enableMouseEvents: true` ersetzt
- `ShiftListView.tsx` → mobile Listen-Ansicht für Schichten
- `useMediaQuery`-Hook neu für Breakpoint-Erkennung
- `ScheduleCalendar.tsx` → `grid-cols-1` statt `grid-cols-7` auf mobil
- `EditableScheduleCalendar.tsx` → Switch zwischen Grid und Liste basierend auf `isMobile`

**Technik:**
```tsx
const isMobile = useMediaQuery('(max-width: 768px)');
if (isMobile) return <ShiftListView shifts={shifts} employees={employees} />;
return <CalendarGridView ... />;
```

---

## Phase 7 — Testing & Qualitätssicherung

> **Warum:** Ohne Tests keine sicheren Refactorings.  
> **Aufwand:** ~8-16 Stunden initial  
> **Risiko bei Nichtumsetzung:** Mittel (Refactoring-Risiko)

### 7.1 Test-Coverage-Ziele definieren

**Status:** ✅ Erledigt 

| Komponente | Ziel | Priorität |
|-----------|------|-----------|
| Backend Auth (JWT, Passwort) | 90% | Hoch |
| Backend CRUD Endpoints | 80% | Hoch |
| Backend TiTO-Proxy/Callback | 85% | Hoch |
| Frontend Login/Auth | 80% | Hoch |
| Frontend Schedule-Ansicht | 60% | Mittel |
| Frontend Employee-CRUD | 70% | Mittel |

### 7.2 Fehlende Integration-Tests ergänzen

**Status:** ✅ Erledigt  

**Neue Testdateien:**
- `test_auth_flow.py` (11 Tests) — Login (success/wrong/nonexistent), Token-geschützte Endpoints (mit/ohne/ungültig), Refresh-Token (gültig/ungültig), Logout, `must_change_password`-Flag nach Passwortänderung, Login nach PW-Änderung
- `test_role_access.py` (10 Tests) — Non-Admin kann nicht: User listen/löschen/admin-create/andere User lesen/andere User updaten. Non-Admin kann: sich selbst lesen/updaten. Admin kann: User löschen/listen/jeden User lesen.

**Verifikation:** `pytest tests -q` → 171 passed (vorher 150).

### 7.3 Frontend-Komponententests

**Status:** ❌ Offen

**Erste Suites:**
```
tests/components/
├── Login.test.tsx
├── ProtectedRoute.test.tsx
├── EmployeeForm.test.tsx
├── ScheduleCalendar.test.tsx
└── Layout.test.tsx
```

**Pro Test:**
- Rendert Komponente mit verschiedenen Props
- Simuliert User-Interaktionen (Klick, Tastatur, Form-Submit)
- Prüft auf korrekte Darstellung (Snapshot oder Assertion)

---

## Phase 8 — Monitoring & Observability

> **Warum:** Ohne Monitoring sieht man Production-Probleme erst, wenn der User sie meldet.  
> **Aufwand:** ~3-4 Stunden  
> **Risiko bei Nichtumsetzung:** Mittel (blinder Flug)

### 8.1 Log-Level-Konfiguration

**Status:** ❌ Offen

**Datei:** `PlanBar - Backend/src/app/core/logging.py`

```python
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
```

### 8.2 Request-ID / Correlation-ID

**Status:** ❌ Offen

**Middleware:**
```python
import uuid

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    with logger.bind(request_id=request_id):
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### 8.3 Sentry / Error-Tracking

**Status:** ❌ Offen

**Backend:**
```bash
pip install sentry-sdk
```
```python
import sentry_sdk
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "development"),
    traces_sample_rate=0.1,
)
```

**Frontend:**
```bash
pnpm add @sentry/react
```
```typescript
import * as Sentry from '@sentry/react';
Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.VITE_ENVIRONMENT,
});
```

---

## Zusammenfassung: Priorisierte Roadmap

```
Woche 1 (Security & Grundlagen)     █████████████████████████████
  Phase 0: Security Cleanup         █████████████████████████████
  Phase 1: Error Handling           █████████████████████████████

Woche 2 (Qualität & CI)             ░░░█████████████████████████
  Phase 2: CI/CD & Code Quality     ░░░█████████████████████████
  Phase 7: Testing                  ░░░░░░░░░░██████████████████

Woche 3 (Performance & UX)          ░░░░░░░░░░░░░░█████████████
  Phase 3: Performance              ░░░░░░░░░░░░░░█████████████
  Phase 4: Accessibility & UX       ░░░░░░░░░░░░░░░░░░█████████

Woche 4 (Infrastruktur & Finale)    ░░░░░░░░░░░░░░░░░░░░███████
  Phase 5: Infrastruktur            ░░░░░░░░░░░░░░░░░░░░███████
  Phase 6: i18n                     ░░░░░░░░░░░░░░░░░░░░░░░░███
  Phase 8: Monitoring               ░░░░░░░░░░░░░░░░░░░░░░░░░░██
```

### Must-Have vor Go-Live (K.O.-Kriterien)

1. ✅  Keine Secrets in git → Phase 0.1-0.4
2. ✅  CORS nicht `*` → Phase 0.5
3. Skipped  `SECRET_KEY` nicht default → Phase 0.6
4. ✅ Admin-Endpoints geschützt → Phase 0.8
5. ✅ CI/CD läuft Tests → Phase 2.1
6. ✅ Error-Handling logged Fehler → Phase 1.1-1.2
7. Skipped Alembic-Migrationen statt `create_all()` → Phase 5.1
8. ✅ Rate-Limiting auf Login → Phase 0.7
9. ✅ JWT-Tokens in HttpOnly-Cookies → Phase 0.9

### Nice-to-Have vor Go-Live

- Code-Splitting (Phase 3.1)
- Skeleton-Screens (Phase 4.5)
- Structured Logging (Phase 5.6)
- Sentry (Phase 8.3)
- i18n (Phase 6.1)

### Nach Go-Live (Phase 2)

- Frontend-Tests (Phase 2.5)
- Unused Packages entfernen (Phase 3.2)
- Alert-Dialog statt `confirm()` (Phase 4.4)
- Keyboard-Support Calendar (Phase 4.2)
- Bundle-Analyse (Phase 3.5)
- PWA/Offline-Support
- E2E-Tests mit Playwright/Cypress

---

## Anhang: Betroffene Dateien pro Phase

| Phase | Datei(en) |
|-------|-----------|
| 0.1 | `.gitignore`, `Infrastructure/.env`, `PlanBar - Backend/.env` |
| 0.2 | `**/.env.example` (neu) |
| 0.3 | `PlanBar - Backend/src/app/main.py` |
| 0.4 | `PlanBar - Frontend/src/app/pages/Login.tsx` |
| 0.5 | `PlanBar - Backend/src/app/main.py`, `PlanBar - Backend/src/app/config.py` |
| 0.6 | `PlanBar - Backend/src/app/config.py` |
| 0.7 | `PlanBar - Backend/src/app/api/v1/users.py` |
| 0.8 | `PlanBar - Backend/src/app/dependencies.py`, `roles.py`, `schedules.py`, `employees.py`, `users.py` |
| 0.9 | `PlanBar - Backend/src/app/dependencies.py`, `PlanBar - Backend/src/app/api/v1/users.py`, `PlanBar - Backend/src/app/schemas/user.py`, `PlanBar - Frontend/src/app/lib/auth.ts`, `PlanBar - Frontend/src/app/lib/api.ts`, `PlanBar - Frontend/src/app/context/AuthContext.tsx`, `PlanBar - Backend/tests/conftest.py` |
| 1.1 | `PlanBar - Frontend/src/app/context/AuthContext.tsx`, `PlanBar - Frontend/src/app/lib/mappers.ts` |
| 1.2 | `PlanBar - Backend/src/app/services/schedule_service.py`, `PlanBar - Backend/src/app/services/tito_callback.py` |
| 1.3 | `PlanBar - Frontend/src/app/lib/api.ts` |
| 1.4 | `PlanBar - Frontend/src/app/lib/api.ts` |
| 1.5 | `PlanBar - Frontend/src/app/pages/Schedule.tsx` |
| 1.6 | `PlanBar - Backend/src/app/db/database.py` |
| 1.7 | `PlanBar - Backend/src/app/middleware/request_size_limit.py` (neu), `PlanBar - Backend/src/app/main.py` |
| 2.1 | `.github/workflows/ci.yml` (neu) |
| 2.2 | `PlanBar - Frontend/` (ESLint/Prettier-Config) |
| 2.3 | `PlanBar - Backend/pyproject.toml` |
| 2.4 | `PlanBar - Frontend/tsconfig.json` (neu), `vite.config.ts` |
| 2.5 | `PlanBar - Frontend/` (Vitest-Setup) |
| 3.1 | `PlanBar - Frontend/src/app/routes.tsx` |
| 3.2 | `PlanBar - Frontend/package.json` |
| 3.3 | `PlanBar - Frontend/src/app/components/ui/` |
| 3.4 | `PlanBar - Frontend/src/app/components/EditableScheduleCalendar.tsx` |
| 3.5 | `PlanBar - Frontend/vite.config.ts` |
| 3.6 | `PlanBar - Backend/src/app/api/v1/employees.py`, `schedules.py`, Frontend-Services |
| 4.1 | Gesamtes Frontend (Calendar, Buttons, Navigation) |
| 4.2 | `EditableScheduleCalendar.tsx` |
| 4.3 | Dialog-Komponenten |
| 4.4 | `Employees.tsx`, `Requests.tsx`, `Roles.tsx`, `Schedule.tsx` |
| 4.5 | Alle Pages (Dashboard, Employees, Schedule, etc.) |
| 4.6 | `Requests.tsx` |
| 5.1 | `alembic.ini`, `migrations/env.py`, `main.py` |
| 5.2 | `PlanBar - Backend/Dockerfile` |
| 5.3 | `Infrastructure/compose.yaml` |
| 5.4 | `PlanBar - Frontend/nginx.conf` |
| 5.5 | `PlanBar - Backend/src/app/api/v1/health.py` |
| 5.6 | `PlanBar - Backend/src/app/core/logging.py` |
| 5.7 | `PlanBar - Backend/src/app/config.py`, .env-Dateien |
| 6.1 | Gesamtes Frontend |
| 6.2 | `EditableScheduleCalendar.tsx`, `ScheduleCalendar.tsx`, `ShiftListView.tsx` (neu), `useMediaQuery.ts` (neu), `package.json` |
| 7.1 | - |
| 7.2 | `PlanBar - Backend/tests/integration/test_auth_flow.py` (neu), `test_role_access.py` (neu) |
| 7.3 | `PlanBar - Frontend/tests/` (neu) |
| 8.1 | `PlanBar - Backend/src/app/core/logging.py` |
| 8.2 | `PlanBar - Backend/src/app/main.py` |
| 8.3 | `PlanBar - Backend/src/app/main.py`, `PlanBar - Frontend/src/main.tsx` |

---

*Erstellt am 27.05.2026 — Basierend auf Codebase-Analyse mit 50 identifizierten Themen.*
