# PlanBar Backend Architektur

Planbar ist eine Applikation für das Management von Schichtplänen für KMUs. Es ermöglicht die automatisierte Erstellung von Schichtplänen über mvit TiTO und bietet über das Frontend eine ansprechende User-Schnittstelle. Das Backend dient als Schnittstelle zwischen Frontend, DB und TiTO.


API-Calls werden vom Frontend abgesetzt und vom Backend angenommen.
Backend wertet Call aus

Jobanforderungen für TiTO werden an den TiTO-Endpunkt /jobs via HTTP Post weitergeleitet.
Usermanagement, Mitarbeiterdaten sowie Ergebnisse von TiTO hält das Backend in einer eigenen DB vor.

## Datenschema

User
- userid
- username (varchar(64))
- role (user/admin)
- email - varchar (regex validated)
- password (encrypted)
- lastlogin - Timestamp
- created - Timestamp

Employee
- employeeid
- userid - foreign key
- contractid - foreign key
- timecardid - foreign key

Contract
- contractid
- weeklyworkinghours
- breaktime
- hiredrole

Timecard
- timecardid
- week
- year
- balance

ShiftWish
- wishid
- emloyeeid - foreign key
- date
- week
- type
- note

Shiftplan
- planid (PK, varchar)
- schedule_id (FK zu Schedule)
- employee_id (FK zu Employee)
- date (date)
- shift_id (varchar)
- start_time (time)
- end_time (time)
- notes (text)
- metadata (JSON - TiTO metadata)
- metrics (JSON - TiTO metrics)
- diagnostics (JSON - TiTO diagnostics)
- created (timestamp)
- updated (timestamp)

**TiTO Result Struktur:**
```json
{
  "metadata": {
    "status": "SUCCESS|FAILED",
    "solveTimeSeconds": 0.01,
    "timestamp": "2026-05-08T13:23:27.904019Z"
  },
  "solution": {
    "assignments": [
      {
        "employeeId": "emp_001",
        "date": "2026-01-02",
        "shiftId": "S_FRUEH",
        "startTime": "06:00",
        "endTime": "14:00"
      }
    ],
    "unassignedRequirements": []
  },
  "metrics": {
    "wishFulfillmentRate": 100.0,
    "totalObjectiveScore": 600,
    "employeeUtilization": {
      "emp_001": 24.0,
      "emp_002": 16.0,
      "emp_003": 8.0
    },
    "violations": {
      "softConstraints": []
    }
  },
  "diagnostics": {
    "isOptimal": true,
    "info": "Optimale Lösung gefunden."
  }
}
```

## Backend-Endpunkte

Basierend auf der Analyse des Frontends und der TiTO API benötigt das Backend folgende Endpunkte:

### 1. Mitarbeiter-Endpunkte (Employee CRUD)
Das Frontend verwaltet Mitarbeiter lokal, Backend muss diese persistent speichern:
- `POST   /api/employees`          # Neuer Mitarbeiter
- `GET    /api/employees`          # Liste aller Mitarbeiter
- `GET    /api/employees/{id}`     # Einzelner Mitarbeiter
- `PUT    /api/employees/{id}`     # Mitarbeiter aktualisieren
- `DELETE /api/employees/{id}`     # Mitarbeiter löschen

### 2. Schichtwunsch-Endpunkte (Request CRUD)
Das Frontend speichert Wünsche im Context, Backend muss persistieren:
- `POST   /api/requests`           # Neuer Wunsch
- `GET    /api/requests`           # Liste aller Wünsche
- `GET    /api/requests/{id}`      # Einzelner Wunsch
- `PUT    /api/requests/{id}`      # Wunsch aktualisieren
- `DELETE /api/requests/{id}`      # Wunsch löschen

### 3. Schichtplan-Endpunkte (Schedule CRUD)
Das Frontend erstellt Schichtpläne, Backend muss TiTO Ergebnisse speichern:
- `POST   /api/schedules`          # Neuer Schichtplan (TiTO Job einreichen)
- `GET    /api/schedules`          # Liste aller Schichtpläne
- `GET    /api/schedules/{id}`     # Einzelner Schichtplan mit TiTO Ergebnis
- `PUT    /api/schedules/{id}`     # Schichtplan aktualisieren
- `DELETE /api/schedules/{id}`     # Schichtplan löschen
- `POST   /api/schedules/{id}/retry`  # TiTO Job neu einreichen

### 4. Rollen-Endpunkte (Role CRUD)
- `POST   /api/roles`              # Neue Rolle
- `GET    /api/roles`              # Liste aller Rollen
- `PUT    /api/roles/{id}`         # Rolle aktualisieren
- `DELETE /api/roles/{id}`         # Rolle löschen

### 5. Vertrag/Zeitkarte-Endpunkte
- `POST   /api/contracts`          # Neuer Vertrag
- `GET    /api/contracts`          # Liste aller Verträge
- `PUT    /api/contracts/{id}`     # Vertrag aktualisieren
- `POST   /api/timecards`          # Neue Zeitkarte
- `GET    /api/timecards`          # Liste aller Zeitkarten
- `PUT    /api/timecards/{id}`     # Zeitkarte aktualisieren

### 6. Benutzer-Endpunkte (User CRUD)
- `POST   /api/users`              # Neuer Benutzer
- `GET    /api/users`              # Liste aller Benutzer
- `PUT    /api/users/{id}`         # Benutzer aktualisieren
- `DELETE /api/users/{id}`         # Benutzer löschen
- `POST   /api/users/{id}/login`   # Login (password verify)

### 7. TiTO Job-Proxy-Endpunkte
Das Backend muss als Proxy zwischen Frontend und TiTO agieren:
- `POST   /api/tito/jobs`          # Proxy an TiTO /jobs
- `GET    /api/tito/jobs/{job_id}` # Proxy an TiTO /jobs/{job_id}
- `POST   /api/tito/jobs/{job_id}/retry`  # Proxy an TiTO /jobs/{job_id}/retry

### 8. Wochenumschalter-Endpunkte
- `GET    /api/schedules/{id}/weeks`  # A/B Wochen abrufen
- `PUT    /api/schedules/{id}/weeks`  # Wochenumschalter setzen

### 9. Schichtdaten-Endpunkte
- `GET    /api/schedules/{id}/shifts`  # Alle Schichten eines Plans
- `GET    /api/schedules/{id}/summary` # Zusammenfassung (heutige Schichten, etc.)

### 10. Metriken-Endpunkte
- `GET    /api/metrics`             # TiTO Metriken
- `GET    /api/metrics/robustness`  # Robustness Metriken

### 11. DLQ & Callback-Endpunkte
- `GET    /api/dlq`                 # Dead Letter Queue
- `GET    /api/callbacks/pending`   # Pending Callbacks

### 12. Health & Status
- `GET    /api/health`              # Backend Health Check
- `GET    /api/tito/health`         # TiTO Health Check

## Zusammenfassung

Das Backend muss folgende Hauptfunktionen erfüllen:

1. **Datenpersistenz** für alle Entitäten (User, Employee, Contract, Timecard, ShiftWish, Schedule, Role, Shiftplan)
2. **TiTO Proxy** für Job-Management (Einreichen, Status, Retry)
3. **TiTO Ergebnis-Speicherung** (Schichtpläne mit TiTO Response)
4. **Authentifizierung/Autorisierung** (JWT, API Keys)
5. **Metriken-Aggregation** (TiTO Metriken + eigene Metriken)
6. **DLQ-Management** (Fehlgeschlagene Jobs)

Die Architektur sieht vor, dass das Backend als **Schnittstelle** zwischen Frontend und TiTO agiert, wobei alle TiTO-Ergebnisse im Backend gespeichert werden, damit das Frontend sie abrufen kann.

## Fehlende Definitionen

Die folgende Definitionen müssen noch erstellt werden:

1. **Backend-DB Schema** - Alle Tabellen mit vollständiger Definition (Datentypen, Constraints, Indexe)
2. **API Request/Response Models** - Pydantic Models für alle Endpunkte
3. **Authentifizierung** - JWT Token Struktur, API Key Format, Role/Permission Model
4. **TiTO Result Parsing** - Transformation von TiTO Response zu Backend Entity
5. **Metriken-Entität** - Struktur für Metriken und Robustness-Metriken
6. **DLQ & Callback** - Struktur für DLQ-Entry und Callback-Status
7. **Wochenumschalter** - A/B-Wochen-Entität
8. **Schichtdaten** - Shift-Entität und Summary-Entität
9. **ER-Modell** - Vollständiges ER-Diagramm mit allen Beziehungen