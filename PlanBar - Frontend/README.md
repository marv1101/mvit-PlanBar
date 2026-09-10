# PlanBar Frontend

## Test-Coverage

Die Frontend-Test-Coverage wird mit `vitest` und `@vitest/coverage-v8` gemessen.

```bash
pnpm test:coverage
```

Erzeugt:
- Text-Report in der Konsole
- JSON-Report (`coverage/coverage-final.json`)
- HTML-Report (`coverage/index.html`)

Die Coverage-Konfiguration liegt in `vitest.config.ts`.
