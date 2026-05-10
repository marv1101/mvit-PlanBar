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

- `tenantId` ist Pflicht, um Mandanten sauber zu trennen.
- Mandantenspezifische Parameter wie Arbeitszeitmodelle, Pausenregeln, Skills oder Sondervereinbarungen müssen konfigurierbar sein.
- Mandanten-Isolation gilt nicht nur für Input, sondern auch für Monitoring, Logs und Fehlerberichte.
- TiTO stellt dabei nur die verarbeitende Schicht dar -> diese muss nicht Mandantenspezifisch sein, aber sicherstellen, dass keine Daten zwischen den Mandanten ausgetauscht werden können

### Monitoring & Betrieb

- TiTO benötigt Health-Checks und Metriken für Queue-Länge, Job-Dauer, Fehlerquote und Solver-Laufzeiten.
- Eine einfache Flask-API kann hier Status- und Statistikendaten liefern.
- Für SaaS sind Performance-Metriken wichtig: Anzahl aktiver Worker, durchschnittliche Durchlaufzeit, Anteil `TIMEOUT`-Jobs.
- Operationalisierung sollte auch Ausbau/Skalierung mehrerer Worker-Instanzen abbilden.

### Sicherheit / Zugriff

- Sensible Planungsdaten im Payload sollten geschützt werden.
- Zugriff auf die Queue und auf die Status-API muss authentifiziert und autorisiert werden.
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
    },
    {
      "id": "S_SPAET",
      "name": "Spätschicht",
      "startTime": "14:00",
      "endTime": "22:00",
      "minBreakMinutes": 30
    }
  ],
  "requirements": [
    {
      "date": "2026-01-01",
      "shiftId": "S_FRUEH",
      "neededSkills": { "Apotheker": 1, "PTA": 2 }
    }
  ],
  "employees": [
    {
      "id": "emp_001",
      "name": "Max Mustermann",
      "contract": {
        "weeklyHours": 40.0,
        "employmentType": "Apotheker",
        "currentBalanceHours": 5.5
      },
      "skills": ["Notdienst", "BTM"],
      "forbiddenDates": ["2026-01-15"]
    }
  ],
  "wishes": [
    {
      "employeeId": "emp_001",
      "type": "OFF",
      "date": "2026-01-01",
      "weight": 5,
      "comment": "Neujahr frei gewünscht"
    },
    {
      "employeeId": "emp_001",
      "type": "PREFER_SHIFT",
      "shiftId": "S_FRUEH",
      "date": "2026-01-02",
      "weight": 2
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
Der Solver muss zwischen harten Gesetzen und weichen Wünschen unterscheiden.

### A. Harte Constraints 
#### Basierend auf dem Arbeitszeitgesetz (ArbZG) und Standardverträgen:

Ruhezeit: 
Mindestens 11 Stunden zwischen dem Ende einer Schicht und dem Beginn der nächsten (§ 5 ArbZG).

Maximalarbeitszeit: 
Verbot von mehr als 10 Stunden Arbeitszeit pro Tag (§ 3 ArbZG).

Pausenregelung: 
Automatischer Abzug/Einplanung von 30 Min. (ab 6 Std.) bzw. 45 Min. (ab 9 Std.) Arbeit.
Die Pause kann individuell pro Mitarbeiter eingeplant werden. Es ist ebenfalls möglich eine Pause von 15 min für das Frühstück (morgens) und eine für das Mittagessen einzuplanen.
Die Pausenzeit ist vertraglich individuell für jeden Mitarbeiter festlegbar. Kollegen können auch 1h pro Tag Pause haben, je nach Vertrag.

Sonntagsruhe: 
Mindestens 15 Sonntage im Jahr müssen beschäftigungsfrei bleiben (§ 11 ArbZG).

Qualifikation: 
Eine Schicht darf nur mit Personal besetzt werden, das den erforderlichen Skill-Tag besitzt (z. B. "Ersthelfer" oder "Kasse").

### B. Weiche Constraints (Optimierungsziele)
Diese fließen in die Objective Function ein. TiTO versucht, diese zu maximieren/minimieren:

Wunscherfüllung: 
Mitarbeiterkönnen den Wunsch für freie Tage oder spezifische Schichten aüßer und dieser wird bestmöglich mit eingeplant.

Gleichverteilung: 
"Fairness-Algorithmus", damit nicht immer dieselbe Person die unbeliebte Samstags-Spätschicht bekommt.

Stundenkonto-Target: 
Minimierung der Abweichung zwischen Ist-Stunden und vertraglichen Soll-Stunden.

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