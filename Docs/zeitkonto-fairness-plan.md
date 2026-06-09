# Zeitkonto & Stunden-Fairness im TiTO Solver

## Implementierungsplan

**Stand:** 2026-06-03  
**Status:** Geplant

---

## Übersicht

Einführung eines Zeitkontos für Mitarbeiter, sodass die Verteilung der Schichten fair getracked werden kann. Pausenzeit zählt nicht als Arbeitszeit. Der TiTO Solver berücksichtigt Fairness über die Stundenverteilung, sodass nicht ein Kollege jede Woche mehr macht als andere mit vergleichbaren Rollen/Fähigkeiten.

---

## Architektur

```
Frontend (React)          Backend (FastAPI)           TiTO (OR-Tools CP-SAT)
       │                        │                            │
       │── Time-Account API ──→ │                            │
       │                        │── Submit mit              │
       │                        │   currentBalanceHours ──→ │
       │                        │                            ├── Stunden-Fairness
       │                        │                            │   (Soft Constraint)
       │                        │── Callback +              │
       │                        │   Timecard-Update ←────── │
       │                        │
       │── Fairness-Meter ←──── │
       │── Wish-Review UI ────→ │── Approved-Wishes nur ──→ │
```

---

## Phase 1: TiTO Solver

### 1a. Employee Schema erweitern

**Datei:** `TiTO/src/tito/schema.py` (Zeilen 84–106)

- Neues Feld `currentBalanceHours: float = 0.0` im `Employee`-Modell
- In `normalize_employee_fields()`: Wert aus `contract.currentBalanceHours` übernehmen (Rückwärtskompatibilität)

```python
class Employee(BaseModel):
    # ... bestehende Felder
    currentBalanceHours: Optional[float] = Field(default=0.0, description="Aktueller Zeitkontostand in Stunden")
```

### 1b. Stunden-Fairness als Soft Constraint

**Datei:** `TiTO/src/tito/solver.py`

**Bestehende Shift-Count-Fairness ersetzen** (Zeilen 170–187):

| ALT | NEU |
|---|---|
| `min_shifts`/`max_shifts` basierend auf Schichtanzahl | Stundenbasierte Fairness als Zielfunktion |
| Hard Constraint (jeder MA: `min <= count <= max`) | Soft Constraint (Minimierung der Abweichung) |
| Alle MA gleich behandelt | Gruppiert nach Skills/Rollen |

**Neue Logik in `solve_model()`:**

#### Rollen-Gruppen ermitteln

- Jeder Skill eines Mitarbeiters definiert eine Gruppenzugehörigkeit
- Ein MA mit mehreren Skills wird in jeder Gruppe anteilig verglichen
- Nur MA mit dem gleichen Skill werden in einer Gruppe gegeneinander fair verteilt

#### Target-Berechnung pro MA

```
Für jede skill-basierte Gruppe:
  total_group_minutes = Summe der eff. Minuten aller Requirements, die diesen Skill benötigen
  total_group_contract_minutes = Summe(contractHours × Wochen) aller MA mit diesem Skill

  Für jeden MA in der Gruppe:
    anteil = contractMinutes / total_group_contract_minutes
    target_minutes = anteil × total_group_minutes
    adjusted_target = target_minutes - (currentBalanceHours × 60)
```

#### Deviations-Variablen

```python
over = cp_model.NewIntVar(0, max_possible, f"over_{emp}")
under = cp_model.NewIntVar(0, max_possible, f"under_{emp}")
cp_model.Add(actual_minutes - adjusted_target == over - under)
```

#### Zielfunktion (Prioritäten)

```python
maximiere: Summe(assignments) × 10000           # Abdeckung (höchste Priorität)
         + Summe(erfüllte Wünsche) × 100        # Wunscherfüllung
         - Summe(over + under) × 1              # Fairness (geringste Priorität)
```

### 1c. Metriken erweitern

**Datei:** `TiTO/src/tito/solver.py` (Zeilen 512–531)

- `currentBalanceHours` in die Metrik-Ausgabe aufnehmen
- Neue Metrik: `projectedBalance` (aktueller Stand + geplante Stunden − Soll-Stunden)
- Neue Metrik: `fairnessDeviation` pro Employee

---

## Phase 2: Backend Integration

### 2a. Zeitkonto-Stand im TiTO-Payload

**Datei:** `PlanBar - Backend/src/app/services/schedule_service.py` (Funktion `_build_tito_payload`)

- Vor Submit: Aktuelle `Timecard.balance` für jeden MA laden (letzter Eintrag nach `year`/`week`)
- Als `currentBalanceHours` im Employee-Entry mitsenden

```python
latest_timecard = (
    db.query(Timecard)
    .filter(Timecard.employee_id == emp.id)
    .order_by(Timecard.year.desc(), Timecard.week.desc())
    .first()
)
entry["currentBalanceHours"] = latest_timecard.balance if latest_timecard else 0.0
```

### 2b. Timecard-Modell erweitern

**Datei:** `PlanBar - Backend/src/app/db/models/employee.py` (Zeilen 58–69)

Neue Spalten:

```python
class Timecard(Base):
    # ... bestehende Felder
    scheduled_hours = Column(Float, default=0.0)   # Vom Solver geplante Stunden
    actual_hours = Column(Float, default=0.0)       # Tatsächlich geleistet (optional, später)
    contract_hours = Column(Float, default=0.0)      # Vertragliche Stunden in dieser Woche
```

**Constraint:** `unique(employee_id, week, year)` für Upsert

### 2c. Timecard-Automatik nach Callback

**Datei:** `PlanBar - Backend/src/app/services/tito_callback.py`

Neue Funktion `update_timecards_from_schedule(db, schedule)`:

- Für jeden Shiftplan: effektive Stunden berechnen (`(end - start) - break`)
- Wochen- und Jahreszahl aus Datum via ISO-Kalender
- Timecard für `(employee_id, week, year)` suchen oder anlegen
- `scheduled_hours` = Summe der effektiven Stunden aus allen Shiftplans der Woche
- `contract_hours` = `weekly_working_hours` aus Contract
- `balance` = Balance der Vorwoche + (`scheduled_hours` − `contract_hours`)
- Wird in `process_tito_callback()` nach dem Speichern der Shiftplans aufgerufen

### 2d. Wish-Review für Admin (Admin-Override)

**Datei:** `PlanBar - Backend/src/app/db/models/shift_wish.py`

`ShiftWish` um Status-Feld erweitern:

- `status`: `pending` | `approved` | `rejected` (Default: `approved` für Rückwärtskompatibilität)
- `reviewed_by`: ForeignKey → `users.id`
- `reviewed_at`: DateTime
- `rejection_reason`: Text (optional)

**API-Endpunkte:**

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/schedules/{id}/wishes/pending` | Alle offenen Wünsche für Schedule |
| `PUT` | `/wishes/{id}/approve` | Wunsch freigeben |
| `PUT` | `/wishes/{id}/reject` | Wunsch ablehnen (mit Begründung) |

**Payload-Generierung anpassen** (`_build_tito_payload`):
- Nur Wünsche mit `status == "approved"` an TiTO senden
- `rejected` Wünsche werden komplett übergangen
- `pending` Wünsche blockieren den Submit (Admin muss erst reviewen)

### 2e. API: Zeitkonto-Endpunkt

**Datei:** `PlanBar - Backend/src/app/api/v1/employees.py`

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/employees/{id}/time-account` | Zeitkonto-Stand + Historie |

**Response-Beispiel:**

```json
{
  "employee_id": 1,
  "current_balance": 5.5,
  "history": [
    {
      "week": 22,
      "year": 2026,
      "scheduled_hours": 38.0,
      "contract_hours": 40.0,
      "delta": -2.0,
      "balance": 3.5
    }
  ],
  "projected": {
    "from_schedule": 42.0,
    "expected_balance_after": 7.5
  }
}
```

---

## Phase 3: Frontend

### 3a. Employee-Detail: Zeitkonto-Anzeige

**Dateien:** `PlanBar - Frontend/src/app/pages/Employees/`, `PlanBar - Frontend/src/app/components/`

Neue Komponente `TimeAccountCard`:

- Aktueller Saldo (Zahl + Farbsignal)
  - Grün: ausgeglichen (±5h)
  - Gelb: leichte Abweichung (±5–15h)
  - Rot: starke Abweichung (> ±15h)
- Wochen-Historie als Tabelle
- Optional: Mini-Chart (recharts) mit Balance-Verlauf

**Neue Type:**

```typescript
interface TimeAccountEntry {
  week: number;
  year: number;
  scheduledHours: number;
  contractHours: number;
  delta: number;
  balance: number;
}

interface EmployeeTimeAccount {
  employeeId: number;
  currentBalance: number;
  history: TimeAccountEntry[];
  projected: {
    fromSchedule: number;
    expectedBalanceAfter: number;
  };
}
```

### 3b. Schedule: Fairness-Meter

**Datei:** `PlanBar - Frontend/src/app/components/ScheduleCalendar/`

Neue Komponente `FairnessMeter`:

- Nutzt `employeeUtilization` aus TiTO-Metriken
- Horizontaler Bar-Chart: Geplante Stunden vs. Vertragsstunden pro MA
- Gruppiert nach Rolle (Farbcodierung)
- Hover-Tooltip mit Details (Anteil, Abweichung, Balance)
- Schwellwert-Markierung bei >10% Abweichung

### 3c. Wish-Review UI

**Datei:** `PlanBar - Frontend/src/app/pages/Requests/` oder neuer Dialog

- Admin sieht beim Schedule-Submit eine Liste aller offenen Wünsche
- Pro Wunsch: Approve/Reject-Buttons + optionales Kommentarfeld bei Reject
- Submit-Button erst aktiv wenn alle Wünsche reviewed sind
- Badge/Count der offenen Wünsche im Schedule-Status

---

## Datenbank-Migrationen (Alembic)

| Schritt | Tabelle | Änderung | Typ |
|---|---|---|---|
| 001 | `timecards` | ADD `scheduled_hours float DEFAULT 0` | Schema |
| 002 | `timecards` | ADD `actual_hours float DEFAULT 0` | Schema |
| 003 | `timecards` | ADD `contract_hours float DEFAULT 0` | Schema |
| 004 | `timecards` | ADD UNIQUE `(employee_id, week, year)` | Constraint |
| 005 | `shift_wishes` | ADD `status varchar(20) DEFAULT 'approved'` | Schema |
| 006 | `shift_wishes` | ADD `reviewed_by integer REFERENCES users(id)` | Schema |
| 007 | `shift_wishes` | ADD `reviewed_at timestamp` | Schema |
| 008 | `shift_wishes` | ADD `rejection_reason text` | Schema |

---

## Implementierungs-Reihenfolge

| Prio | Modul | Beschreibung | Aufwand |
|---|---|---|---|
| **P1** | TiTO: Schema | `currentBalanceHours` in Employee | ~15 Min |
| **P1** | TiTO: Solver | Stunden-Fairness (Soft Constraint) + Rollen-Gruppen | ~2h |
| **P1** | Backend: Payload | `currentBalanceHours` im Submit-Payload | ~30 Min |
| **P1** | Backend: Callback | Timecard-Automatik nach Callback | ~1h |
| **P2** | Backend: Timecard-Modell | Migration + neue Felder | ~30 Min |
| **P2** | Backend: Wish-Review | Status-Feld + API-Endpunkte | ~1h |
| **P2** | Backend: API | Zeitkonto-Endpunkt | ~30 Min |
| **P3** | Frontend: TimeAccountCard | Zeitkonto-Anzeige im Employee-Detail | ~1h |
| **P3** | Frontend: FairnessMeter | Stundenverteilungs-Chart im Schedule | ~1h |
| **P3** | Frontend: Wish-Review | Admin-UI für Wunsch-Freigabe | ~1.5h |

**Gesamtaufwand:** ca. 9–10 Stunden

---

## Offene Fragen

- [ ] Soll das Zeitkonto auch manuell korrigierbar sein (z.B. via Admin)?
- [ ] Soll der Fairness-Meter auch negative Salden (MA hat "Minusstunden") anzeigen?
- [ ] Werden bereits existierende (vor der Implementierung) Timecards korrekt eingelesen?
