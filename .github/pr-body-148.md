# Pull Request

## Issue

Closes #148 — `[AUDIT] sync.py _apply_action: 9-Pfad-If-Kaskade (3 Resourcen × 3 Actions)`

## Was ändert sich?

`sync.py._apply_action()` (114 Zeilen, 24 Verzweigungen, 3 verstreute Auth-Checks) wird in **5 single-responsibility Action-Klassen + 1 Registry** aufgeteilt. Der HTTP-Endpoint `POST /api/v1/sync/actions` ruft nach dem Refactoring nur noch `SyncActionRegistry.dispatch()` auf — Auth-Check an exakt **einer** Stelle.

## Vorher / Nachher

| Metrik | Vorher | Nachher |
|--------|--------|---------|
| `_apply_action()` Zeilen | 114 | 0 (komplett gelöscht) |
| Verzweigungen pro Action | 9–24 | ≤ 6 |
| Auth-Check-Stellen | 3 (verstreut) | 1 (im Registry-Dispatcher) |
| Action-Klassen | 0 (Inline-If-Kaskade) | 5 (`CreateShiftWish`, `UpdateShiftWish`, `DeleteShiftWish`, `UpdateSchedule`, `UpdateShift`) |
| Unit-Tests für Action-Pfade | 0 | 10 |

## Architektur

```
src/app/services/sync_actions/
├── __init__.py           # Action-Klassen + Registry exportieren
├── base.py               # RoleRequired (permissive default) + SyncAction
├── registry.py           # SyncActionRegistry (register/get/dispatch/reset)
├── serializers.py        # Extrahierte *_serialize-Helper (brechen den
│                         # Zirkel-Import zwischen sync.py und den Actions)
├── create_shift_wish.py  # requests/create
├── update_shift_wish.py  # requests/update
├── delete_shift_wish.py  # requests/delete
├── update_schedule.py    # schedules/update (admin only, ETag-Conflict-Check)
└── update_shift.py       # shifts/update
```

**Action-Interface (jede Klasse, ≤ 50 Zeilen):**

```python
class RoleRequired:
    def check(self, user: User) -> None: ...  # raise HTTPException(403) on deny

class CreateShiftWish(RoleRequired):
    resource = "requests"
    action = "create"
    role = EmployeeRoleCheck()

    @staticmethod
    def execute(db, data, user) -> dict: ...
```

**Registry (single auth choke-point):**

```python
class SyncActionRegistry:
    _by_key: dict[tuple[str, str], Any] = {}

    @classmethod
    def dispatch(cls, payload, db, user):
        handler = cls.get(payload.resource, payload.action)  # 400 if unsupported
        handler.role.check(user)                              # central auth
        return handler.execute(db, payload.data, user)
```

## Verletzte SOLID-Prinzipien — behoben

| Prinzip | Vorher | Nachher |
|---------|--------|---------|
| **SRP** (Single Responsibility) | Datensammlung, Filterung, Formatierung, Serialisierung in einer Funktion | Jede Action-Klasse = genau eine Verantwortlichkeit |
| **OCP** (Open/Closed) | Neue (resource, action) = Edit im Monolithen | Neue Action = neue Datei + 1 Zeile in `__init__.py` |
| **DRY** | Update-Pfad kopiert Felder mit `if "field" in data: setattr(...)` 3× wiederholt | Einheitlicher Loop in `UpdateShift._EDITABLE_FIELDS` |
| **Testbarkeit** | Integration-Test pro (resource, action) nötig | Unit-Tests pro Action-Klasse, isoliert von der DB-Orchestrierung |

## Tests

- **10/10 neue Unit-Tests grün** in `tests/unit/test_sync_actions.py`
- **473/473 gesamte Suite grün** (463 vorherige + 10 neue)
- `ruff check .` clean für alle neuen und geänderten Dateien
- `ruff format .` clean

### Test-Coverage der Strategy-Pattern-Dateien

| Datei | Abdeckung |
|-------|-----------|
| `sync_actions/base.py` | 100% |
| `sync_actions/registry.py` | 100% |
| `sync_actions/create_shift_wish.py` | Happy-Path + Default-Pfad |
| `sync_actions/update_shift_wish.py` | Happy-Path + 404-Not-Found |
| `sync_actions/delete_shift_wish.py` | Happy-Path |
| `sync_actions/update_schedule.py` | Happy-Path |
| `sync_actions/update_shift.py` | Happy-Path inkl. Type-Coercion für Date/Time-Felder |

## Architektur-Entscheidungen

1. **Klassen statt reiner Funktionen** — `RoleRequired` ist als vererbbarer Strategy-Knoten designt, nicht als `Protocol`. Dadurch kann jede Action-Klasse ihre eigene `role`-Instanz als Klassen-Attribut halten, und der Dispatcher ruft `handler.role.check(user)` direkt auf — keine `isinstance`-Checks nötig.
2. **`@staticmethod execute()`** — vermeidet implizites `self`. Tests rufen `CreateShiftWish.execute(db, data, user)` direkt auf; das matched das Mock-Setup (`mock_action.execute.assert_called_once_with(db, data, user)` ohne `self`).
3. **Serialisierer in eigenes Modul** — `sync.py` braucht sie für `initial_sync` und `delta_sync`, die Action-Klassen brauchen sie für ihre Returns. Beide Importe in einem Modul führen zu einem Zirkel. Lösung: dediziertes `serializers.py` mit `serialize_*` (ohne Underscore-Prefix), importiert als `_serialize_*` in sync.py und den Actions.
4. **Local Import im Endpoint** — `from app.services.sync_actions import SyncActionRegistry` passiert im `sync_actions()`-Body, nicht am Modul-Top. Das hält den `app.services.sync_actions`-Import-Pfad optional (kein Hard-Failure bei `app.api.v1.sync`-Lade-Problemen), und ruff meldet es mit `noqa: PLC0415`.
5. **Input-Coercion in `UpdateShift`** — SQLite `Date`-Spalten brauchen `date`-Objekte, `Time`-Spalten brauchen `time`-Objekte, der Client schickt ISO-Strings. Der Coercion-Loop parst nur die Felder, die auch wirklich gesetzt sind, und konvertiert Strings inline.

## Was sich NICHT ändert

- **API-Contract unverändert**: `POST /api/v1/sync/actions` mit `{actions: [{resource, action, data, client_timestamp}]}` — der Response-Shape (results[], errors[]) bleibt identisch.
- **Keine Alembic-Migration nötig** — reines Refactoring, keine Schema-Änderung.
- **Keine Verhaltensänderung** — die Original-Logik (Owner-or-Admin-Check für Wishes, Admin-only für Schedules, beliebiger User für Shifts) bleibt 1:1 erhalten.
- **Kein neues Package / keine neue Dependency**.

## Verwandte Issues / Schwester-Dateien

- **Part of AUDIT-Cluster #149–#157** (God-Function / God-Component / Coverage-Lücken cleanup)
- Trägt zur Schließung des Meta-Audit-Issues **#157** bei
- Schwester-Pattern für `SwimlaneCalendar.tsx` (1014 Zeilen, Issue **#146** PR 1) folgt demselben Strategy-Pattern
