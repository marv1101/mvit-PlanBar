# TiTO

Der *Ti*me*t*able *O*ptimizer ist eine Softwarekomponente von MVIT PlanBar. TiTO ist der zentrale Optimizer für die Zeitplanung im PlanBar-System.

## Anforderungen

TiTO wird über an eine Queue angebunden. Dabei werden aus der Queue die Jobs mit der höchsten Priorität oder die ältesten entnommen und verarbeitet. Die Daten werden in der Queue im JSON-Format abgelegt. Nach der Berechnung wird von TiTO ebenfalls ein JSON-Objekt in die Response-Queue gelegt, welches die gesamte Zeitplanung für den gewünschten Zeitraum inkl. berücksichtigter Wünsche enthält. TiTO soll vor allem für die Schichtplanung verwendet werden. Damit gilt es das Deutsche Arbeitsrecht zu berücksichtigen, da der potentielle Markt kleine Unternehmen in Deutschland sind. Durch den Aufbau als Worker für eine Queue, soll es möglich sein verschiedene TiTO-Instanzen auf einer Queue laufen zu lassen. Somit kann eine höhere parallelität der Aufgaben erreicht werden. Die Schichtplanung soll als Optimierungsproblem über Google OR-Tools aufgegriffen werden. Hier gilt es zusätzlich zu deutschen Regulierungen auch verschiedene Pausenzeiten, Arbeitszeitmodelle, Urlaube und Wünsche der Mitarbeiter zu berücksichtigen.

## Techstack - Grob

- Python
- Flask - WebAPI for Stats
- PostgreSQL - Jobqueue in Tabelle
- Google OR-Tools - Solver
- **Pydantic** - Schema-Validierung und Typsicherheit (ab Phase 8)

## Systemarchitektur & Datenfluss

TiTO ist bewusst als Queue-basierter Worker gebaut. Die Entkopplung über PostgreSQL ermöglicht, dass mehrere TiTO-Instanzen parallel Jobs aus derselben Queue verarbeiten, während die Jobsache selbst in JSON kodiert bleibt.

### Job-Lifecycle und Queue-Verhalten

- Eingehende Jobs werden in einer Queue-Tabelle als JSON gespeichert.
- Der Worker nimmt priorisierte oder die ältesten Jobs an, markiert sie als in Bearbeitung und verarbeitet sie.
- Es sollte eine klare Job-Statussteuerung geben: `queued`, `processing`, `failed`, `completed`.
- Wiederholte Ausführung desselben Jobs muss idempotent sein oder durch eindeutige `jobId`-Prüfung verhindert werden.
- Fehlerfälle benötigen einen Retry-Mechanismus und eine Dead Letter Queue für nicht verarbeitbare Jobs.
- `callback_queue` kann als Ziel für das Ergebnis bzw. als Hinweis für Rückantwort-Mechanismen dienen.

### Validierung und Schema-Versionierung

- TiTO validiert jedes Job-Payload mit Pydantic für Typsicherheit und automatische Validierung.
- Das Schema ist versionsfähig über `schemaVersion` im Config-Objekt.
- Änderungen am Input-Format müssen rückwärtskompatibel bleiben oder klar dokumentiert werden.
- Das Modell sollte alle relevanten Daten enthalten: Mandant, Job-Metadaten, Schichten, Mitarbeiter, Anforderungen, Wünsche und Verfügbarkeiten.
- API-Dokumentation ist über `GET /openapi.json` verfügbar und kann in Swagger UI oder ReDoc verwendet werden.
- **Phase 8**: Migration von `jsonschema` zu **Pydantic** für bessere Typsicherheit, IDE-Unterstützung und automatische Validierung.

### Timeout / Fallback-Verhalten

- OR-Tools kann bei komplexen Plänen lange rechnen. Für SaaS ist ein festes Timeout wichtig.
- Wenn die Zeit abläuft, sollte TiTO idealerweise die beste bis dahin gefundene Lösung liefern und nicht nur einen Fehler zurückgeben.
- Der Output muss den Solver-Status explizit ausweisen: `SUCCESS`, `FEASIBLE`, `INFEASIBLE`, `TIMEOUT`.
- Bei `TIMEOUT` sollten ergänzende Diagnosedaten zur Qualität der Zwischenlösung zurückgegeben werden.

### Multi-Tenancy und Mandantenbetrieb

- `tenantId` ist Pflicht im Job-Metadata, um Mandanten sauber zu trennen.
- Mandantenspezifische Parameter wie Arbeitszeitmodelle, Pausenregeln, Skills oder Sondervereinbarungen müssen konfigurierbar sein.
- Mandanten-Isolation gilt nicht nur für Input, sondern auch für Monitoring, Logs und Fehlerberichte.
- TiTO stellt dabei nur die verarbeitende Schicht dar -> diese muss nicht Mandantenspezifisch sein, aber sicherstellen, dass keine Daten zwischen den Mandanten ausgetauscht werden können.

#### Implementierte Tenant-Isolation

TiTO implementiert eine logische Mandantentrennung auf Code-Ebene (Defense-in-Depth), die sowohl im Database-per-Tenant-Betrieb als auch im Shared-Instance-Betrieb sicher ist:

- **Schema-Validierung beim Enqueue**: `POST /jobs` validiert das Payload gegen das Pydantic-Schema; `tenantId` (≥1) ist Pflicht. Ungültige Jobs werden mit `400` abgelehnt und erreichen nie die Queue.
- **IDOR-Schutz**: Mandanten-scoped Tokens (via `API_TOKEN_TENANTS` oder JWT `tenant_id`) dürfen nur für ihren eigenen Tenant einreichen. Ein Mismatch zwischen Token-Tenant und Payload-Tenant liefert `403`.
- **Tenant-scoped Lesezugriffe**: `/jobs`, `/jobs/{id}`, `/dlq`, `/callbacks/pending` filtern Ergebnisse nach dem authentifizierten Tenant. Cross-Tenant-Abfragen liefern `404` bzw. leere Listen.
- **Mandanten-isolierte Metrics**: `/metrics`, `/metrics/robustness`, `/metrics/prometheus` aggregieren nur Jobs des authentifizierten Tenants.
- **Mandanten-scoped Idempotenz**: Composite-Unique-Index `(tenant_id, idempotency_key)` — derselbe Key darf pro Tenant unabhängig existieren, Kollisionen zwischen Mandanten sind ausgeschlossen.
- **Typkonsistenz**: `tenant_id` wird überall als `str` normalisiert (DB-Spalte ist `TEXT`), um Typ-Mismatch-bedingte Filterfehler zu vermeiden.

#### Rollen-Modell

TiTO unterscheidet vier Token-Rollen (via `API_TOKEN_ROLES` oder JWT `role`):

| Rolle | Erlaubte Endpunkte | Tenant-Kontext |
|-------|-------------------|----------------|
| `admin` | Alle | Ja (aus `API_TOKEN_TENANTS` oder JWT) |
| `worker` | `/workers/*` | Kein (Worker verarbeitet alle Jobs) |
| `metrics` | `/metrics` | Ja |
| `jobs` | `/jobs` | Ja |

#### Umgebungsvariablen für Tenant-Isolation

| Variable | Beschreibung |
|----------|-------------|
| `API_TOKEN` / `API_TOKENS` | Kommaseparierte API-Tokens (Default-Rolle: `admin`) |
| `API_TOKEN_ROLES` | Mapping `token=role,token=role` (z. B. `key1=admin,key2=worker`) |
| `API_TOKEN_TENANTS` | Mapping `token=tenant_id` für mandanten-scoped Tokens |
| `WORKER_API_TOKEN` | Dediziertes Worker-Token (bevorzugt über `API_TOKENS[0]`) |
| `JWT_SECRET` | JWT-Signierschlüssel |
| `JWT_ALGORITHMS` | Erlaubte JWT-Algorithmen (Default: `HS256`) |
| `JWT_AUDIENCE` | Optional: erwartete JWT-Audience |
| `JWT_ISSUER` | Optional: erwarteter JWT-Issuer |

### Monitoring & Betrieb

- TiTO benötigt Health-Checks und Metriken für Queue-Länge, Job-Dauer, Fehlerquote und Solver-Laufzeiten.
- Eine einfache Flask-API kann hier Status- und Statistikdaten liefern.
- Für SaaS sind Performance-Metriken wichtig: Anzahl aktiver Worker, durchschnittliche Durchlaufzeit, Anteil `TIMEOUT`-Jobs.
- Operationalisierung sollte auch Ausbau/Skalierung mehrerer Worker-Instanzen abbilden.

### Sicherheit / Zugriff

- Sensible Planungsdaten im Payload sollten geschützt werden.
- Zugriff auf die Queue und auf die Status-API muss authentifiziert und autorisiert werden.
- Token-basierte Authentifizierung via API-Key (`Authorization: Bearer` oder `X-API-Key`) oder JWT.
- Rollen-Modell (`admin`, `worker`, `metrics`, `jobs`) steuert ressourcenspezifische Berechtigungen.
- Mandanten-scoped Tokens begrenzen Lese-/Schreibzugriff auf den eigenen Tenant.
- Worker verwenden ein dediziertes `WORKER_API_TOKEN` mit Rolle `worker` (kein Admin-Zugriff).
- Ebenso ist Verschlüsselung der Daten im Transit und bei Bedarf im Ruhezustand sinnvoll aber nicht Teil des MVP.

### Erweiterungen für das Datenmodell

- Das JSON-Modell sollte Verfügbarkeiten als harte vs. weiche Einschränkungen unterscheiden.
- Split-Shifts und Teilzeitmodelle sollten als eigene Objekte oder Attribute abgebildet werden.
- Weitere Regeln wie maximale Wochenenden, Rotation oder Rollentrennung sollten als optionale Constraint-Parameter erfasst werden.

Eingabe (PostgreSQL Eintrag in Queue Tabelle): Ein JSON-Objekt, das den "Planungszeitraum" definiert.
Metadaten: tenant_id, priority, callback_queue.
Stammdaten: Mitarbeiter (IDs, Skills, Vertragsstunden), Schichtmodelle (Früh, Spät, Nacht).
Variablen: Zeitbereich, genehmigte Urlaube, konkrete Schichtwünsche.

Verarbeitung: TiTO validiert das JSON gegen ein Schema, übersetzt die Anforderungen in ein mathematisches Modell für OR-Tools und startet den Solver.

Ausgabe (PostgreSQL Eintrag in Queue Tabelle): Ein JSON-Objekt mit dem Ergebnis.
Status: (SUCCESS, FEASIBLE, INFEASIBLE, TIMEOUT).
Assignments: Liste von Zuordnungen (Mitarbeiter X -> Schicht Y).
Metrics: Score der Optimierung (wie viele Wünsche wurden erfüllt?).

### Datenstruktur JSON-Input

{
  "metadata": {
    "jobId": "uuid-1234-5678",
    "tenantId": 42,
    "priority": 1,
    "timestamp": "2026-04-22T10:00:00Z"
  },
  "config": {
    "schemaVersion": "1.0",
    "startDate": "2026-01-01",
    "endDate": "2026-01-31",
    "maxConsecutiveDays": 6,
    "minRestTimeHours": 11
  },
  "shiftTemplates": [
    {
        "id": "S_FRUEH",
        "name": "Frühschicht",
        "startTime": "06:00",
        "endTime": "14:00",
        "minBreakMinutes": 30
    }
  ]
}

### Datenstruktur JSON-Outpput

{
  "metadata": {
    "jobId": "uuid-1234-5678",
    "status": "SUCCESS",
    "solveTimeSeconds": 1.45,
    "timestamp": "2026-04-22T10:05:00Z"
  },
  "solution": {
    "assignments": [
      {
        "employeeId": "emp_001",
        "date": "2026-01-02",
        "shiftId": "S_FRUEH",
        "startTime": "06:00",
        "endTime": "14:00"
      },
      {
        "employeeId": "emp_002",
        "date": "2026-01-02",
        "shiftId": "S_SPAET",
        "startTime": "14:00",
        "endTime": "22:00"
      }
    ],
    "unassignedRequirements": []
  },
  "metrics": {
    "wishFulfillmentRate": 92.5,
    "totalObjectiveScore": 4500,
    "employeeUtilization": {
      "emp_001": 38.5,
      "emp_002": 40.0
    },
    "violations": {
      "softConstraints": [
        {
          "type": "WISH_NOT_MET",
          "employeeId": "emp_001",
          "date": "2026-01-05",
          "description": "Wunsch auf Spätschicht konnte nicht erfüllt werden."
        }
      ]
    }
  },
  "diagnostics": {
    "isOptimal": true,
    "info": "Alle harten Constraints erfüllt. Optimale Lösung im Zeitrahmen gefunden."
  }
}

## Der Solver-Kern (Logik & Constraints)

Der Solver verwendet Google OR-Tools CP-SAT. Entscheidend ist die Trennung zwischen **harten Gesetzen** (ArbZG/JArbSchG/MuSchG — werden verletzungsunfähig erzwungen) und **weichen Zielen** (Objective Function).

### A. Harte Constraints

#### Arbeitsrecht (ArbZG, JArbSchG, MuSchG)

Ruhezeit (§ 5 ArbZG):
Mindestens 11 Stunden zwischen dem Ende einer Schicht und dem Beginn der nächsten. Berechnung auf Basis **absoluter Zeitstempel**, korrekt für Mitternacht überschreitende Schichten (Nachtdienst 22:00–06:00). Für Schichtarbeiter konfigurierbar verkürzbar auf bis zu 9h (§ 21 ArbZG).

Tagesmaximum (§ 3 ArbZG):
Maximal 10h effektive Arbeitszeit pro Tag. Die Arbeitszeit wird **netto** gemessen (§ 2 Abs. 1 ArbZG): gesetzliche/vertragliche Ruhepausen zählen **nicht** zur Arbeitszeit. Die Pausenregelung wird kumulativ über den gesamten Arbeitstag berechnet (auch bei Teilschichten). Zusätzlich eine gesetzliche Wochenobergrenze von 48h (Durchschnitt, konservativ als Wochen-Cap umgesetzt).

Pausenregelung (§ 4 ArbZG):
Automatischer Abzug/Einplanung — **exakte Grenzwerke**: 30 Min. bei **mehr als 6 bis 9 Stunden**, 45 Min. bei **mehr als 9 Stunden** (bei exakt 6,0h bzw. 9,0h keine bzw. nur 30 Min.). Die Pause kann individuell pro Mitarbeiter und pro Schichttemplate überschrieben werden (max. aus Gesetz/Template/Vertrag).

Sonn-/Feiertagsschonung (§ 9/§ 11 ArbZG):
Mindestens 15 Sonntage im Jahr beschäftigungsfrei. Feiertage werden wie Sonntage gewertet. Pro-rata-Näherung auf den Planungszeitraum (Half-Up-Rundung) abzüglich eines vom Aufrufer übergebenen Jahressaldos (`protectedDaysWorkedYTD`). Nach Sonntagsarbeit ist ein Ersatzruhetag binnen 2 Kalenderwochen zu gewähren, nach Feiertagsarbeit (auf Werktag) binnen 8 Wochen (§ 11 Abs. 3).

Qualifikation (hart, B1):
Eine Schicht darf **ausschließlich** mit Personal besetzt werden, das die geforderten Skills **und** (bei `ROLE_`-Skills) die passende Rolle besitzt. Unqualifizierte oder gesperrte Mitarbeiter (`forbiddenDates`) werden niemals geplant — inklusive einer INFEASIBLE-Diagnose, falls eine Schicht niemandem zugewiesen werden kann.

Nachtarbeit (§ 6 ArbZG):
Nachtarbeitnehmer (über isNightWorker-Flag) dürfen an Nachtschichten maximal 10h arbeiten (Netto). Fehlende oder älter als 1 Jahr abgelaufene arbeitsmedizinische Eignungsuntersuchung (§ 6 Abs. 1) wird als SOFT-Verletzung gemeldet.

Jugendarbeitsschutz (JArbSchG, vereinfachte Kernregeln):
Minderjährige (`isMinor`) unterliegen 12h Ruhezeit, max. 8h/Tag, max. 40h/Woche, max. 5 Werktage/Woche sowie einem Verbot der Nachtarbeit (20:00–06:00) und der Arbeit an Samstagen, Sonn- und Feiertagen.

Mutterschutz (MuSchG):
Über `protectionUntil` gesperrte Tage werden als absolute Beschäftigungsverbote erzwungen.

Teilschichten / Split-Shifts:
Mehrere Schichten desselben Arbeitstags sind zulässig; Ruhezeit (§ 5) gilt zwischen Arbeitstagen, nicht zwischen Teilschichten. Überlappende Schichten sind stets verboten.

#### Planungslogische Constraints

Wochenstunden (Vertrag): Effektive Arbeitszeit pro ISO-Woche ≤ Vertrag (inkl. Vorperioden, `preShifts`).
max. aufeinanderfolgende Arbeitstage (Default 6) über **echte Kalendertage** (Lücken unterbrechen die Kette).
Schicht-Rotation: max. gleiche Schicht hintereinander (konfigurierbar).

### B. Objective Function (Zielfunktungsgewichte, B8)

Die Gewichte sind so proportioniert, dass harte Pflichten dominieren und Ziele sich sinnvoll steuern:

| Priorität | Ziel | Gewicht pro Einheit |
|---|---|---|
| 1 | Pflicht-Slot besetzt | +100.000 |
| 2 | Wunsch erfüllt | +2.000 × weight (1–10) |
| 3 | Fairness-Abweichung (Pflicht-Arbeit) | −50 / Minute |
| 4 | Optionaler Slot gefüllt (nur maximizeStaffing) | +60 / Netto-Minute |
| 5 | Balance-Recovery (Zeitkonto) | ±1,04 / Min. × Saldo |

Pflicht-Zuweisungen dominieren alles. Wünsche überwiegen eine Fairness-Abweichung von bis ca. 20–40 Minuten. Optionale Slots werden nur bei `maximizeStaffing` gefüllt (Fairness bleibt anreizfrei, damit optionale Kapazität ohne Flag leer bleibt).

### C. Diagnose bei INFEASIBLE (D6)

Fehlende Planbarkeit wird nicht still gemeldet. Stattdessen: statische Analyse (Skills, Rollen, Verfügbarkeit) und gezielte Re-Löstung mit entspannten Constraint-Familien (`infeasibilityReasons` im Output).

### D. Vorperioden / Cross-Schedule-Kontinuität (C8)

Über das `preShifts`-Feld können bereits fixierte Schichten (andere Pläne, Drafts, 7-Tage-Fenster vor Planstart) übergeben werden. Sie fließen in Ruhezeit, Folgetage-Ketten, Wochenstunden und Sonntagsquoten ein.

## 3. Tech-Stack & Implementierungsdetails
### Komponente Technologie Zweck
Sprache: Python 3.11
Hohe Entwicklungsgeschwindigkeit, beste OR-Tools Anbindung. 
SolverGoogle OR-Tools (CP-SAT) State-of-the-art Constraint Programming.
PostgreSQL als Queue zur Entkopplung von Web-Backend und Rechenlast.

Monitoring:
- Flask / Prometheus/stats Endpunkt für Queue-Länge
- Rechenzeit pro Job und Health-Checks
  
Validierung: 
Pydantic
Sicherstellen, dass das eingehende JSON valide und vollständig ist.

## 4. Besondere Herausforderungen für KMU

Im deutschen Mittelstand gibt es oft "historisch gewachsene" Besonderheiten, die TiTO handhaben sollte:
Teilschichten (Split Shifts): Besonders in der Gastronomie. Ein Mitarbeiter arbeitet von 11:00-14:00 und wieder von 17:00-22:00. Die Ruhezeit von 11 Stunden muss nach der letzten Teilschicht beginnen.

Verfügbarkeits-Typen: Unterschied zwischen "Ich möchte hier nicht arbeiten" (weich) und "Ich kann hier absolut nicht arbeiten wegen Kinderbetreuung" (hart).

Rollen-Rotation: Vermeidung von Monotonie (z.B. nicht mehr als 3 Tage hintereinander in der Kühlkammer).

"Timeout" für den Solver. Bei komplexen Plänen kann OR-Tools ewig nach der perfekten Lösung suchen. KMU-Anwender bevorzugen meist eine Lösung, die "zu 98% perfekt" ist, aber nach 5 Sekunden vorliegt, statt 10 Minuten auf das absolute Optimum zu warten.