# Frontend: Umfassende Test-Abdeckung implementieren

## User Story

**Als** Entwickler und QA-Verantwortlicher  
**will ich** eine umfassende Test-Abdeckung für das PlanBar Frontend  
**damit** Regressionen frühzeitig erkannt, die Code-Qualität gesichert undRefactorings sicher durchgeführt werden können.

---

## Problemstellung

Das PlanBar Frontend hat aktuell **keinerlei Tests** (keine Unit-, Komponenten- oder E2E-Tests). Das bedeutet:

- Jede Änderung kann unbemerkt Bugs einführen
- Refactorings sind risikoreich
- Keine Dokumentation der erwarteten Funktionsweise
- Keine Sicherheit bei Deployment-Updates

Die Analyse (OpenCode Executive Summary) identifizierte dies als **hochprioritäres Risiko**.

---

## Gesamtziel

Aufbau einer mehrschichtigen Test-Strategie nach dem Testing Pyramid:

```
        ▲
       / \      E2E-Tests (Playwright)
      /   \     ~10-15 kritische Flows
     /─────\
    /       \   Integrationstests (Vitest + MSW)
   /         \  ~30-40 Komponenten-Tests
  /───────────\
 /             \ Unit-Tests (Vitest)
/               \ ~60-80 Utility/Service-Tests
─────────────────
```

---

## Scope & Priorisierung

### Phase 1: Foundation (Priorität: Kritisch)

| ID | Task | Aufwand | Beschreibung |
|----|------|---------|--------------|
| T1.1 | Test-Infrastruktur aufsetzen | 2h | Vitest + jsdom + React Testing Library + MSW konfigurieren |
| T1.2 | Auth-Tests schreiben | 3h | Login/Logout, Token-Handling, ProtectedRoute |
| T1.3 | API-Client-Tests | 2h | Axios-Interceptor, Error-Handling, BaseURL |
| T1.4 | Login-Seite Tests | 3h | Form-Validierung, Submit-Verhalten, Error-States |

### Phase 2: Core Business Logic (Priorität: Hoch)

| ID | Task | Aufwand | Beschreibung |
|----|------|---------|--------------|
| T2.1 | Service-Layer-Tests | 4h | employeeService, roleService, userService, scheduleService, requestService |
| T2.2 | Context-Tests | 3h | AuthContext, AppContext (State-Management, Side-Effects) |
| T2.3 | Utility-Tests | 2h | mappers.ts, week.ts, timezone.ts |
| T2.4 | Schedule-Seite Tests | 4h | Kalender-Rendering, Shift-Logik, Drag&Drop-States |

### Phase 3: Komponenten-Tests (Priorität: Mittel)

| ID | Task | Aufwand | Beschreibung |
|----|------|---------|--------------|
| T3.1 | EmployeeForm Tests | 3h | Validierung, Submit, Edit-Modus |
| T3.2 | ScheduleCalendar Tests | 3h | Rendering, Navigation, Events |
| T3.3 | EditableScheduleCalendar | 4h | Komplexe Interaktionen, Inline-Editing |
| T3.4 | RequestForm Tests | 2h | Formular-Logik, Status-Übergänge |
| T3.5 | Layout & ProtectedRoute | 2h | Routing, Role-Checks |

### Phase 4: E2E-Tests (Priorität: Mittel)

| ID | Task | Aufwand | Beschreibung |
|----|------|---------|--------------|
| T4.1 | Playwright Setup | 2h | Config, Fixtures, CI-Integration |
| T4.2 | Login-Flow E2E | 2h | Kompletter Login including RBAC |
| T4.3 | Schedule-Management E2E | 3h | Shift erstellen/bearbeiten/löschen |
| T4.4 | Employee-CRUD E2E | 2h | Mitarbeiter anlegen/bearbeiten |
| T4.5 | Request-Workflow E2E | 2h | Antrag stellen/bearbeiten genehmigen |

---

## Technische Anforderungen

### Test-Framework Stack

```json
{
  "devDependencies": {
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "@testing-library/user-event": "^14.0.0",
    "msw": "^2.0.0",
    "jsdom": "^24.0.0",
    "@playwright/test": "^1.40.0",
    "@vitest/coverage-v8": "^1.0.0"
  }
}
```

### Verzeichnisstruktur

```
src/
├── __tests__/
│   ├── unit/
│   │   ├── lib/
│   │   │   ├── api.test.ts
│   │   │   ├── auth.test.ts
│   │   │   ├── mappers.test.ts
│   │   │   ├── week.test.ts
│   │   │   └── timezone.test.ts
│   │   ├── services/
│   │   │   ├── employeeService.test.ts
│   │   │   ├── roleService.test.ts
│   │   │   ├── userService.test.ts
│   │   │   ├── scheduleService.test.ts
│   │   │   └── requestService.test.ts
│   │   └── contexts/
│   │       ├── AuthContext.test.tsx
│   │       └── AppContext.test.tsx
│   ├── integration/
│   │   ├── Login.test.tsx
│   │   ├── Schedule.test.tsx
│   │   ├── Employees.test.tsx
│   │   ├── EmployeeForm.test.tsx
│   │   ├── RequestForm.test.tsx
│   │   ├── ScheduleCalendar.test.tsx
│   │   └── ProtectedRoute.test.tsx
│   └── fixtures/
│       ├── handlers.ts          # MSW Request Handlers
│       ├── server.ts            # MSW Server Setup
│       └── data/
│           ├── employees.ts
│           ├── schedules.ts
│           └── users.ts
├── test/
│   ├── setup.ts                 # Vitest Setup
│   └── vitest.config.ts
e2e/
├── playwright.config.ts
├── fixtures/
│   └── auth.fixture.ts
├── Login.spec.ts
├── Schedule.spec.ts
├── Employees.spec.ts
└── Requests.spec.ts
```

### Mocking-Strategie

1. **API-Layer (MSW)**: Alle HTTP-Requests werden über Mock-Service-Worker abgefangen
2. **React Context**: Test-Wrapper mit konfigurierbarem Context-Wert
3. **Browser-APIs**: `vi.fn()` für localStorage, navigator, etc.
4. **React Router**: `createMemoryRouter` für Routing-Tests

---

## Akzeptanzkriterien

### AC-1: Test-Infrastruktur
- [ ] Vitest läuft mit `pnpm test`
- [ ] Coverage-Report wird generiert ( Ziel: >70% Statements)
- [ ] MSW interceptet API-Calls in Tests
- [ ] React Testing Library ist konfiguriert

### AC-2: Unit-Tests (Phase 1+2)
- [ ] `api.ts`: BaseURL, Interceptor, Error-Handling getestet
- [ ] `auth.ts`: Token-Storage, Logout, isExpired getestet
- [ ] `mappers.ts`: Alle Mapping-Funktionen getestet
- [ ] Services: Jede Methode hat positive + negative Tests

### AC-3: Integrationstests (Phase 2+3)
- [ ] Login: Validierung, Success, Failure getestet
- [ ] ProtectedRoute: Redirect bei keinem Token, Role-Check
- [ ] Schedule: Rendering mit leeren/vollen Daten
- [ ] Employees: CRUD-Operationen mit Mock-Daten

### AC-4: E2E-Tests (Phase 4)
- [ ] Login-Flow funktioniert mit Playwright
- [ ] Schedule-Erstellung durchspielbar
- [ ] Tests laufen in CI (GitHub Actions)

### AC-5: Code-Qualität
- [ ] `tsc --noEmit` läuft fehlerfrei
- [ ] ESLint-Pipeline ohne Errors
- [ ] Keine `@ts-ignore` oder `any`-Typen in Tests

---

## Test-Beispiele

### Beispiel 1: API-Client Unit-Test

```typescript
// src/__tests__/unit/lib/api.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import api from '@/lib/api'

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Base Configuration', () => {
    it('should have correct baseURL', () => {
      expect(api.defaults.baseURL).toBe('/api')
    })

    it('should include credentials in requests', () => {
      expect(api.defaults.withCredentials).toBe(true)
    })
  })

  describe('Error Interceptor', () => {
    it('should redirect to login on 401', async () => {
      // Test implementation
    })

    it('should show toast on network error', async () => {
      // Test implementation
    })
  })
})
```

### Beispiel 2: Login-Seite Integration Test

```typescript
// src/__tests__/integration/Login.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Login } from '@/pages/Login'
import { AuthProvider } from '@/context/AuthContext'
import { server } from '../fixtures/server'
import { http, HttpResponse } from 'msw'

describe('Login Page', () => {
  it('should show validation errors for empty fields', async () => {
    render(<Login />)
    
    await userEvent.click(screen.getByRole('button', { name: /anmelden/i }))
    
    expect(screen.getByText(/email ist erforderlich/i)).toBeInTheDocument()
    expect(screen.getByText(/passwort ist erforderlich/i)).toBeInTheDocument()
  })

  it('should call API with correct credentials', async () => {
    const loginSpy = vi.fn()
    server.use(
      http.post('/api/auth/login', async ({ request }) => {
        loginSpy(await request.json())
        return HttpResponse.json({ success: true })
      })
    )

    render(<Login />)
    
    await userEvent.type(screen.getByLabelText(/email/i), 'user@example.com')
    await userEvent.type(screen.getByLabelText(/passwort/i), 'password123')
    await userEvent.click(screen.getByRole('button', { name: /anmelden/i }))

    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledWith({
        email: 'user@example.com',
        password: 'password123'
      })
    })
  })

  it('should show error message on failed login', async () => {
    server.use(
      http.post('/api/auth/login', () => {
        return HttpResponse.json(
          { detail: 'Ungültige Anmeldedaten' },
          { status: 401 }
        )
      })
    )

    render(<Login />)
    
    await userEvent.type(screen.getByLabelText(/email/i), 'wrong@example.com')
    await userEvent.type(screen.getByLabelText(/passwort/i), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /anmelden/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/ungültige anmeldedaten/i)
    })
  })
})
```

### Beispiel 3: ScheduleCalendar Integration Test

```typescript
// src/__tests__/integration/ScheduleCalendar.test.tsx
import { render, screen, within } from '@testing-library/react'
import { ScheduleCalendar } from '@/components/ScheduleCalendar'
import { createMockSchedule } from '../fixtures/data/schedules'

describe('ScheduleCalendar', () => {
  it('should render week header with correct dates', () => {
    const schedule = createMockSchedule({ weekStart: '2024-01-15' })
    render(<ScheduleCalendar schedule={schedule} />)
    
    expect(screen.getByText(/KW 3/i)).toBeInTheDocument()
    expect(screen.getByText(/15\. Januar/i)).toBeInTheDocument()
  })

  it('should display shifts for each employee', () => {
    const schedule = createMockSchedule({
      employees: [
        { id: '1', name: 'Max Mustermann', shifts: [...] }
      ]
    })
    render(<ScheduleCalendar schedule={schedule} />)
    
    expect(screen.getByText('Max Mustermann')).toBeInTheDocument()
    // More assertions for shift rendering
  })

  it('should call onSelectShift when clicking a shift', async () => {
    const onSelect = vi.fn()
    const schedule = createMockSchedule({ hasShifts: true })
    
    render(<ScheduleCalendar schedule={schedule} onSelectShift={onSelect} />)
    
    await userEvent.click(screen.getByTestId('shift-cell-1'))
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({
      id: expect.any(String)
    }))
  })
})
```

---

## CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Frontend Tests

on:
  push:
    paths:
      - 'PlanBar - Frontend/**'
  pull_request:
    paths:
      - 'PlanBar - Frontend/**'

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: 'PlanBar - Frontend'
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: pnpm/action-setup@v2
        with:
          version: 8
          
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'pnpm'
          cache-dependency-path: 'PlanBar - Frontend/pnpm-lock.yaml'
          
      - run: pnpm install --frozen-lockfile
      
      - name: Type Check
        run: pnpm tsc --noEmit
        
      - name: Lint
        run: pnpm eslint src --ext .ts,.tsx
        
      - name: Unit & Integration Tests
        run: pnpm test:coverage
        
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          directory: './coverage'
          flags: frontend
          
  e2e:
    needs: test
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: 'PlanBar - Frontend'
    
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'pnpm'
          
      - run: pnpm install --frozen-lockfile
      - run: pnpm exec playwright install --with-deps chromium
      
      - name: E2E Tests
        run: pnpm test:e2e
        
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

---

## Definition of Done

- [ ] Alle Tests schreiben grün
- [ ] Coverage >70% Statements (Vitest)
- [ ] `tsc --noEmit` ohne Fehler
- [ ] ESLint ohne Errors
- [ ] E2E-Tests in CI grün
- [ ] PR auf `dev` Branch
- [ ] Code-Review durchgeführt
- [ ] Doku im README ergänzt

---

## Referenzen

- [Vitest Docs](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [MSW](https://mswjs.io/)
- [Playwright](https://playwright.dev/)
- Executive Summary (siehe vorherige Analyse)

---

## Acceptance Criteria (Kurzform)

1. ✅ `pnpm test` läuft fehlerfrei
2. ✅ Coverage >70% Statements
3. ✅ `pnpm test:e2e` läuft fehlerfrei
4. ✅ CI-Pipeline implementiert
5. ✅ Keine `@ts-ignore` in Test-Dateien
