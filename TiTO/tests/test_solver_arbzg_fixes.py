"""Regressionstests für die ArbZG-Logik-Fixes im Solver.

Deckt die in der Logikprüfung gefundenen Fehlerfälle ab:

1. Fairness-Metrik deckungsgleich zum Modell (nur Pflicht-Slots vs. Vertragsanteil,
   ohne optionale Slots und ohne Zeitkontostand in der Abweichung).
2. Ersatzruhetag (§ 11 Abs. 3): Ein Tag mit preShift ist kein freier Ersatztag.
3. Wochenlimit nutzt denselben tageskumulierten § 4-Pausenabzug wie das Tageslimit.
4. neededSkills mit Zaehler 0 erzeugt keinen Slot (kein unsichtbarer mandatory-Slot).
5. unassignedRequirements zählt Pflicht-/Optional-Slots slot-genau.
"""

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tito.solver import build_model, solve_model


def _sunday_payload(with_pre_shift: bool) -> dict:
    """Sonntag + 14 Folgetage je 1h-Requirement (alle außer Tag +5), ein MA.

    Ohne Fix erfüllt der Solver den Ersatzruhetag über Tag+5, obwohl dort
    (mit preShift) gearbeitet wird -> mit preShift muss es INFEASIBLE sein.
    """
    import datetime

    sunday = datetime.date(2026, 1, 4)
    assert sunday.isoweekday() == 7
    dates = [(sunday + timedelta(days=i)).isoformat() for i in range(15)]
    no_req_date = dates[5]

    requirements = [
        {"shiftId": "t1", "date": d, "startTime": "00:00", "endTime": "01:00"} for d in dates if d != no_req_date
    ]
    payload = {
        "metadata": {"tenantId": 1},
        "config": {
            "startDate": dates[0],
            "endDate": dates[-1],
            "maxConsecutiveDays": 15,
            "minFreeSundaysPerYear": 0,
        },
        "shiftTemplates": [{"id": "t1", "name": "T", "startTime": "00:00", "endTime": "01:00"}],
        "requirements": requirements,
        "employees": [{"id": "e1", "name": "A", "skills": [], "contractHours": 40}],
    }
    if with_pre_shift:
        payload["preShifts"] = [{"employeeId": "e1", "date": no_req_date, "startTime": "12:00", "endTime": "13:00"}]
    return payload


def test_fairness_deviation_ignores_optional_slots_and_balance():
    """Modell-Strafe misst nur Pflicht-Slots vs. Vertragsanteil: optionale Slots
    und der Zeitkontostand duerfen die gemeldete Abweichung nicht veraendern."""
    # Teil B: Pflicht-Anteile exakt erfuellt -> Abweichung 0 despite optionalen Slots
    payload = {
        "metadata": {"tenantId": 1},
        "config": {"startDate": "2026-01-05", "endDate": "2026-01-06", "maximizeStaffing": True},
        "shiftTemplates": [{"id": "t1", "name": "T", "startTime": "08:00", "endTime": "16:00"}],
        "requirements": [
            {"shiftId": "t1", "date": "2026-01-05", "count": 1, "maxCount": 2},
            {"shiftId": "t1", "date": "2026-01-06", "count": 1, "maxCount": 2},
        ],
        "employees": [
            {"id": "e1", "name": "A", "skills": [], "contractHours": 40},
            {"id": "e2", "name": "B", "skills": [], "contractHours": 20},
        ],
    }
    result = solve_model(build_model(payload), timeout_seconds=30)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")

    fairness = result["metrics"]["employeeFairness"]
    assert len(result["solution"]["assignments"]) == 4
    # scheduledHours enthaelt weiterhin optionale Slot-Zeiten
    assert {f["scheduledHours"] for f in fairness.values()} == {15.0}
    assert fairness["e1"]["targetHours"] == 10.0
    assert fairness["e2"]["targetHours"] == 5.0
    # Jeder MA hat einen Pflicht-Anteil von 7.5h: Modell-Abweichung = |7.5-10| = 2.5.
    # Die alte Metrik haette durch die optionalen Slots 5.0 (e1) bzw. 10.0 (e2)
    # gemeldet – optionale Slots duerfen die Abweichung nicht vergroessern.
    assert fairness["e1"]["fairnessDeviation"] == 2.5
    assert fairness["e2"]["fairnessDeviation"] == 2.5

    # Teil B: currentBalanceHours darf die Abweichung nicht verfaelschen.
    # Der Solver verteilt auf e2 (positiver Saldo bestraft Zuweisung an e1),
    # die gemeldete Abweichung bleibt die pure Modell-Abweichung.
    payload = {
        "metadata": {"tenantId": 1},
        "config": {"startDate": "2026-01-05", "endDate": "2026-01-06"},
        "shiftTemplates": [{"id": "t1", "name": "T", "startTime": "08:00", "endTime": "16:00"}],
        "requirements": [{"shiftId": "t1", "date": "2026-01-05", "count": 1}],
        "employees": [
            {"id": "e1", "name": "A", "skills": [], "contractHours": 40, "currentBalanceHours": 12.5},
            {"id": "e2", "name": "B", "skills": [], "contractHours": 40},
        ],
    }
    result = solve_model(build_model(payload), timeout_seconds=30)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    fairness = result["metrics"]["employeeFairness"]
    assigned_emp = result["solution"]["assignments"][0]["employeeId"]
    assert assigned_emp == "e2"
    # Ziel je MA = 40/80 * 7.5h = 3.75h; e2 arbeitet 7.5h Pflicht:
    # Abweichung beidseitig 3.75. Die alte Formel haette bei e1 durch den
    # Zeitkontostand 8.75 gemeldet — Balance darf nicht einmessen.
    assert fairness["e1"]["targetHours"] == 3.75
    assert fairness["e1"]["fairnessDeviation"] == 3.75
    assert fairness["e2"]["fairnessDeviation"] == 3.75
    # projectedBalance bleibt eine reine Information (inkl. Saldo)
    assert fairness["e1"]["projectedBalance"] == 8.75


def test_ersatz_rest_day_without_pre_shift_is_free():
    result = solve_model(build_model(_sunday_payload(with_pre_shift=False)), timeout_seconds=30)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) == 14


def test_ersatz_rest_day_with_pre_shift_is_not_free():
    result = solve_model(build_model(_sunday_payload(with_pre_shift=True)), timeout_seconds=30)
    assert result["metadata"]["status"] == "INFEASIBLE"


def test_weekly_limit_uses_cumulative_daily_break():
    """Split-Shift: 2 x 5h am selben Tag bei 9.5h-Wochenvertrag.

    § 4 verlangt am Tag 10h Brutto 45 min Pause -> 9h15 Netto; der Wochenlimit-
    Term muss denselben Tagespausenabzug nutzen (früher wurde pausenlos 10h
    gezahlt -> fälschlich INFEASIBLE).
    """
    payload = {
        "metadata": {"tenantId": 1},
        "config": {"startDate": "2026-01-05", "endDate": "2026-01-06"},
        "shiftTemplates": [
            {"id": "t1", "name": "T1", "startTime": "08:00", "endTime": "13:00"},
            {"id": "t2", "name": "T2", "startTime": "15:00", "endTime": "20:00"},
        ],
        "requirements": [
            {"shiftId": "t1", "date": "2026-01-05", "count": 1},
            {"shiftId": "t2", "date": "2026-01-05", "count": 1},
        ],
        "employees": [{"id": "e1", "name": "A", "skills": [], "contractHours": 9.5}],
    }
    result = solve_model(build_model(payload), timeout_seconds=30)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assigned = result["solution"]["assignments"]
    assert len(assigned) == 2
    assert {a["shiftId"] for a in assigned} == {"t1", "t2"}


def test_zero_needed_skill_count_creates_no_slot():
    """neededSkills mit Zaehler 0 darf keinen mandatory-Slot erzwingen."""
    base = {
        "metadata": {"tenantId": 1},
        "config": {"startDate": "2026-01-05", "endDate": "2026-01-06"},
        "shiftTemplates": [{"id": "t1", "name": "T", "startTime": "08:00", "endTime": "16:00"}],
    }

    # Nur Zaehler 0 -> gar kein Slot: keine Zuweisungen, keine unbesetzten Requirements
    payload = base | {
        "requirements": [{"shiftId": "t1", "date": "2026-01-05", "neededSkills": {"SKILL_A": 0}}],
        "employees": [{"id": "e1", "name": "A", "skills": ["SKILL_A"]}],
    }
    result = solve_model(build_model(payload), timeout_seconds=15)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert result["solution"]["assignments"] == []
    assert result["solution"]["unassignedRequirements"] == []

    # Gemischt 1x SKILL_A + 0x SKILL_B: MA ohne SKILL_B bleibt zuweisbar
    payload = base | {
        "requirements": [{"shiftId": "t1", "date": "2026-01-05", "neededSkills": {"SKILL_A": 1, "SKILL_B": 0}}],
        "employees": [{"id": "e1", "name": "A", "skills": ["SKILL_A"]}],
    }
    result = solve_model(build_model(payload), timeout_seconds=15)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) == 1
    assert result["solution"]["assignments"][0]["employeeId"] == "e1"


def test_unassigned_report_counts_mandatory_and_optional_slots_exactly():
    """Fix 5: slot-genaue Zaehlung — mandatory_missing wird pro Slot ermittelt
    statt per Count-Differenz (die einen optional besetzten Slot fälschlich
    als Pflichtabdeckung zaehlt). Bei count=2 und nur einem MA ist die
    Lösung hard-infeasible; bei maxCount bleibt der Report-Fall SOFT."""
    # Pflicht doppelt belegt mit nur einem MA -> INFEASIBLE (kein Fake-Report)
    payload = {
        "metadata": {"tenantId": 1},
        "config": {"startDate": "2026-01-05", "endDate": "2026-01-06"},
        "shiftTemplates": [{"id": "t1", "name": "T", "startTime": "08:00", "endTime": "16:00"}],
        "requirements": [{"shiftId": "t1", "date": "2026-01-05", "count": 2}],
        "employees": [{"id": "e1", "name": "A", "skills": [], "contractHours": 40}],
    }
    result = solve_model(build_model(payload), timeout_seconds=15)
    assert result["metadata"]["status"] == "INFEASIBLE"
    assert result["solution"]["assignments"] == []
    assert result["solution"]["unassignedRequirements"] == []

    # Unbesetzter optionaler Slot (Gruppen-Regel verbietet doppelte Besetzung
    # durch denselben MA): Report SOFT, Pflicht-Slot exakt gezählt (0 fehlt)
    payload = {
        "metadata": {"tenantId": 1},
        "config": {"startDate": "2026-01-05", "endDate": "2026-01-06"},
        "shiftTemplates": [{"id": "t1", "name": "T", "startTime": "08:00", "endTime": "16:00"}],
        "requirements": [{"shiftId": "t1", "date": "2026-01-05", "count": 1, "maxCount": 2}],
        "employees": [{"id": "e1", "name": "A", "skills": [], "contractHours": 40}],
    }
    result = solve_model(build_model(payload), timeout_seconds=15)
    assert len(result["solution"]["assignments"]) == 1
    unassigned = result["solution"]["unassignedRequirements"]
    assert len(unassigned) == 1
    assert unassigned[0]["missingCount"] == 1
    violation = result["metrics"]["violations"][0]
    assert violation["severity"] == "SOFT"
    assert violation["details"] == {"missingCount": 1, "mandatoryMissing": 0}
