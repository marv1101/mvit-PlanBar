# API Versioning Plan für TiTO

## TL;DR
Implementierung von API-Versioning mittels URL-Pfad-Versioning (`/api/v1/...`, `/api/v2/...`) mit Unterstützung für Header-basierte Versionierung. Der Plan umfasst Migration der bestehenden Endpunkte, Version-Management-Infrastruktur, Deprecation-Strategie und Backward-Compatibility-Mechanismen.

---

## Schritte

### Phase 1: Analyse & Design (Abhängigkeit: keine)

1. **Bestehende Endpunkte inventarisieren**
   - Alle Endpunkte in `api.py` dokumentieren
   - Identifizieren welche Endpunkte versioniert werden müssen
   - Bestimmen welche Endpunkte versionierungsfrei bleiben (`/health`, `/metrics`, `/openapi.json`)

2. **Versionierungsstrategie definieren**
   - URL-Pfad-Versioning als primäre Strategie (`/api/v1/jobs`, `/api/v2/jobs`)
   - Header-Versioning als Alternative (`Accept: application/vnd.tito.v1+json`)
   - Deprecation-Policy festlegen (Warnungen ab v1, Sunset ab v0)

3. **Version-Konfigurationsstruktur erstellen**
   - Version-Schema in `config.py` hinzufügen
   - Version-zu-Endpoint-Mapping definieren
   - Default-Version festlegen (empfohlen: `v1`)

### Phase 2: Infrastruktur (parallel mit Phase 3 möglich)

4. **Version-Management-Module erstellen**
   - `src/tito/versioning.py`: Version-Detection, Migration-Logik
   - `src/tito/versioning/migrations.py`: Schema-Migrationen zwischen Versionen
   - `src/tito/versioning/deprecation.py`: Deprecation-Warnungen

5. **API-Router aktualisieren**
   - Version-Präfix `/api/v{version}/` vor alle versionierten Endpunkte
   - Fallback-Logik für fehlende Versionen
   - Default-Route für nicht-existierende Versionen

6. **OpenAPI-Spezifikation erweitern**
   - Versionierte Pfade in OpenAPI dokumentieren
   - `x-versions` Extension für Version-Informationen
   - Deprecation-Labels für alte Versionen

### Phase 3: Endpunkt-Migration (parallel mit Phase 2 möglich)

7. **Job-Endpunkte migrieren**
   - `/jobs` → `/api/v1/jobs`
   - `/jobs/{job_id}` → `/api/v1/jobs/{job_id}`
   - Payload-Schema-Anpassungen pro Version

8. **Worker-Endpunkte migrieren**
   - `/workers/*` → `/api/v1/workers/*`
   - Request/Response-Format-Anpassungen

9. **Metrics-Endpunkte versionierungsfrei lassen**
   - `/health`, `/metrics`, `/openapi.json` bleiben unverändert
   - Optional: `/api/v1/metrics` für konsistente Struktur

### Phase 4: Testing & Dokumentation

10. **Version-Spezifische Tests schreiben**
    - Tests für v1-Endpunkte
    - Tests für v2-Endpunkte (falls vorhanden)
    - Migration-Tests zwischen Versionen
    - Deprecation-Warnung-Tests

11. **Dokumentation aktualisieren**
    - API-Usage-Guide mit Version-Informationen
    - Migration-Guide für Clients
    - Deprecation-Notices dokumentieren

### Phase 5: Deployment & Monitoring

12. **Deployment-Strategie**
    - Parallelbetrieb alter und neuer Versionen
    - Gradual Rollout (Canary Deployment)
    - Monitoring für Version-Usage-Statistiken

13. **Monitoring-Endpunkte erweitern**
    - Version-Usage-Metriken
    - Deprecation-Warning-Counts
    - Migration-Error-Rates

---

## Relevante Dateien

- `src/tito/api.py` — Haupt-API-Implementierung
- `src/tito/config.py` — Konfiguration
- `src/tito/schema.py` — Pydantic-Schemas
- `tests/` — Test-Dateien
- `docs/api-documentation.md` — API-Dokumentation
- `docs/api-versioning-plan.md` — **Dieser Plan**

---

## Verifikation

1. **Smoke-Tests**: Alle Endpunkte erreichbar mit verschiedenen Versionen
2. **Integration-Tests**: Versionierte Endpunkte funktionieren korrekt
3. **Deprecation-Tests**: Warnungen werden korrekt zurückgegeben
4. **OpenAPI-Validierung**: Spezifikation ist gültig und vollständig
5. **Load-Tests**: Parallelbetrieb mehrerer Versionen stabil

---

## Entscheidungen

- **Primäre Strategie**: URL-Pfad-Versioning (`/api/v1/...`)
- **Fallback-Strategie**: Header-Versioning (`Accept-Version: v1`)
- **Default-Version**: `v1` (aktuelle Implementierung)
- **Deprecation-Fenster**: 6 Monate nach Sunset-Datum
- **Version-Naming**: SemVer (`v1.0.0`, `v1.1.0`)

---

## Weitere Überlegungen

### Backward Compatibility
Wie gehen wir mit Clients, die keine Version angeben?
- *Empfehlung*: Default auf `v1`, mit deprecation warning

### Schema-Evolution
Wie handhaben wir Breaking Changes?
- *Empfehlung*: Neue Major-Version für Breaking Changes

### Migration-Pfad
Wie migrieren wir Daten zwischen Versionen?
- *Empfehlung*: Migration-Module mit Daten-Transformation

---

**Status**: Plan erstellt, bereit zur Diskussion und Approval.
**Erstellt**: 14. Mai 2026
**Autor**: TiTO Development Team
