"""Regressions- und Regeltests für den TiTO-Solver.

Diese Tests bilden das KORREKTE Verhalten ab (ArbZG/JArbSchG/MuSchG-Regeln
sowie behobene Solver-Bugs B1-B19 / C1-C10 / D1-D7 aus dem Code-Review).
"""

from datetime import datetime, timedelta, timezone

import pytest
from tito.solver import build_model, solve_model

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FRUEH = {"id": "S_FRUEH", "startTime": "06:00", "endTime": "14:00"}
SPAET = {"id": "S_SPAET", "startTime": "14:00", "endTime": "22:00"}
NACHT = {"id": "S_NACHT", "startTime": "22:00", "endTime": "06:00"}


def _emp(emp_id, **kwargs):
    base = {"id": emp_id, "forbiddenDates": [], "contractHours": 40.0}
    base.update(kwargs)
    return base


def _run(payload, timeout=30):
    return solve_model(build_model(payload), timeout_seconds=timeout)


# ---------------------------------------------------------------------------
# B1: Ungültige (Mitarbeiter, Requirement)-Paare müssen hart verboten sein
# ---------------------------------------------------------------------------


def test_unqualified_employee_never_assigned():
    """Mandatory-Requirement ohne qualifizierten Mitarbeiter -> INFEASIBLE statt Zuweisung eines Unqualifizierten."""
    payload = {
        "metadata": {"jobId": "b1-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}}],
        "employees": [_emp("emp_001", skills=["PKA"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] == "INFEASIBLE"
    assert result["solution"]["assignments"] == []


def test_unqualified_not_used_to_cover_unassignable_requirement():
    """Der Solver darf unqualifizierte Mitarbeiter nicht als Lückenfüßer einsetzen (B1)."""
    payload = {
        "metadata": {"jobId": "b1-b"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH, SPAET],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_SPAET", "neededSkills": {"Apotheker": 1}},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "neededSkills": {"Apotheker": 1}},
        ],
        "employees": [
            _emp("emp_001", skills=["Apotheker"]),
            _emp("emp_002", skills=["PKA"]),
        ],
        "wishes": [],
    }
    result = _run(payload)
    # emp_001 kann wegen 8h-Ruhezeit nur eine der beiden Schichten übernehmen,
    # emp_002 ist unqualifiziert -> zwingend INFEASIBLE (statt emp_002 zuzuweisen)
    assert result["metadata"]["status"] == "INFEASIBLE"


def test_forbidden_date_is_hard_constraint():
    """forbiddenDates muss die Zuweisung hart verhindern (B1)."""
    payload = {
        "metadata": {"jobId": "b1-c"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1}],
        "employees": [_emp("emp_001", forbiddenDates=["2026-01-02"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] == "INFEASIBLE"


def test_role_requirement_enforced_hard():
    """ROLE_-Skills erfordern Skill UND passende Rolle (B1/B7)."""
    base = {
        "metadata": {"jobId": "b1-d"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "neededSkills": {"ROLE_APO": 1}}],
        "wishes": [],
    }
    # Falsche Rolle trotz Skill -> INFEASIBLE
    payload = dict(base, employees=[_emp("emp_001", skills=["ROLE_APO"], role="PKA")])
    assert _run(payload)["metadata"]["status"] == "INFEASIBLE"

    # Richtige Kombination -> SUCCESS
    payload = dict(base, employees=[_emp("emp_002", skills=["ROLE_APO"], role="APO")])
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) == 1
    assert result["solution"]["assignments"][0]["employeeId"] == "emp_002"


# ---------------------------------------------------------------------------
# B2: Keine Mehrfachzuweisungen pro Requirement-Slot
# ---------------------------------------------------------------------------


def test_no_duplicate_employee_per_shift_group():
    """Kein Mitarbeiter erhält zwei Slots derselben (date, shiftId)-Gruppe."""
    payload = {
        "metadata": {"jobId": "b2-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 3}],
        "employees": [_emp("emp_001", skills=["Apotheker"]), _emp("emp_002", skills=["Apotheker"])],
        "wishes": [],
    }
    result = _run(payload)
    # count=3 mit nur 2 zuteilbaren MA (Doppelbesetzung verboten) -> INFEASIBLE
    assert result["metadata"]["status"] == "INFEASIBLE"


# ---------------------------------------------------------------------------
# B3: Ruhezeit bei Mitternacht überschreitenden Schichten (absolute Zeiten)
# ---------------------------------------------------------------------------


def test_overnight_shift_rest_time_computed_correctly():
    """Nachtschicht 22:00-06:00 + Frühschicht ab 10:00 am Folgetag = nur 4h Ruhe -> verboten (B3)."""
    template_frueh_10 = {"id": "S_FRUEH10", "startTime": "10:00", "endTime": "18:00"}
    payload = {
        "metadata": {"jobId": "b3-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "minRestTimeHours": 11},
        "shiftTemplates": [NACHT, template_frueh_10],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_NACHT", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_FRUEH10", "count": 1},
        ],
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] == "INFEASIBLE", (
        "Nachtschicht endet 06:00 am Folgetag, Frueschicht beginnt 10:00 -> nur 4h Ruhe (11h gefordert)"
    )


def test_overnight_shift_rest_time_sufficient_gap_allowed():
    """Nachtschicht + Schicht ab 17:00 am Folgetag = 11h Ruhe -> erlaubt (B3 Gegenprobe)."""
    template_abend = {"id": "S_ABEND", "startTime": "17:00", "endTime": "21:00"}
    payload = {
        "metadata": {"jobId": "b3-b"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "minRestTimeHours": 11},
        "shiftTemplates": [NACHT, template_abend],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_NACHT", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_ABEND", "count": 1},
        ],
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) == 2


def test_rest_time_normal_days_enforced():
    """Spätschicht bis 22:00 + Frühschicht ab 06:00 = 8h Ruhe -> verboten (§ 5 ArbZG)."""
    payload = {
        "metadata": {"jobId": "b3-c"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "minRestTimeHours": 11},
        "shiftTemplates": [FRUEH, SPAET],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_SPAET", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] == "INFEASIBLE"


# ---------------------------------------------------------------------------
# B4: Wünsche ohne weight (nur priority) dürfen nicht crashen
# ---------------------------------------------------------------------------


def test_wish_with_priority_only_no_crash():
    """PREFER_SHIFT-Wunsch nur mit priority (kein weight) -> kein TypeError (B4)."""
    payload = {
        "metadata": {"jobId": "b4-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1}],
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [
            {"employeeId": "emp_001", "type": "PREFER_SHIFT", "shiftId": "S_FRUEH", "date": "2026-01-02", "priority": 5}
        ],
    }
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert result["metrics"]["wishFulfillmentRate"] == 100.0


# ---------------------------------------------------------------------------
# B6: Keine Müllwerte bei INFEASIBLE/TIMEOUT
# ---------------------------------------------------------------------------


def test_infeasible_reports_empty_metrics():
    """Bei INFEASIBLE dürfen keine Phantom-Metriken aus uninitialisierten Werten entstehen (B6)."""
    payload = {
        "metadata": {"jobId": "b6-a"},
        "config": {
            "startDate": "2026-01-01",
            "endDate": "2026-01-07",
            "maxDailyWorkHours": 10,
            "minRestTimeHours": 11,
        },
        "shiftTemplates": [FRUEH, SPAET],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_SPAET", "count": 1},
        ],
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [{"employeeId": "emp_001", "type": "PREFER_SHIFT", "shiftId": "S_FRUEH", "date": "2026-01-02"}],
    }
    result = _run(payload)
    assert result["metadata"]["status"] == "INFEASIBLE"
    assert result["solution"]["assignments"] == []
    assert result["solution"]["unassignedRequirements"] == []
    assert result["metrics"]["wishFulfillmentRate"] == 0.0
    assert result["metrics"]["totalObjectiveScore"] == 0
    assert result["metrics"]["employeeUtilization"] == {"emp_001": 0.0}


def test_timeout_without_solution_reports_no_phantom_assignments():
    """Bei TIMEOUT ohne Lösung müssen assignments/metris leer sein (B6)."""
    employees = [_emp(f"emp_{i:03d}", skills=["Apotheker"]) for i in range(1, 26)]
    requirements = []
    day = datetime(2026, 3, 2, tzinfo=timezone.utc)
    for d in range(12):
        for _ in range(5):
            requirements.append(
                {"date": (day + timedelta(days=d)).strftime("%Y-%m-%d"), "shiftId": "S_FRUEH", "count": 1}
            )
    wishes = [
        {
            "employeeId": f"emp_{i:03d}",
            "type": "PREFER_SHIFT",
            "shiftId": "S_FRUEH",
            "date": "2026-03-03",
            "priority": 10,
        }
        for i in range(1, 26)
    ]
    payload = {
        "metadata": {"jobId": "b6-b"},
        "config": {"startDate": "2026-03-02", "endDate": "2026-03-14", "minFreeSundaysPerYear": 0},
        "shiftTemplates": [FRUEH],
        "requirements": requirements,
        "employees": employees,
        "wishes": wishes,
    }
    result = _run(payload, timeout=0.02)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE", "TIMEOUT")
    if result["metadata"]["status"] == "TIMEOUT":
        assert result["solution"]["assignments"] == []
        assert result["metrics"]["wishFulfillmentRate"] == 0.0
        assert result["metrics"]["totalObjectiveScore"] == 0


# ---------------------------------------------------------------------------
# B15: Objective-Score ist der echte Zielfunktionswert
# ---------------------------------------------------------------------------


def test_total_objective_score_is_real_objective_value():
    """totalObjectiveScore muss den echten CP-SAT-Zielwert widerspiegeln (B15)."""
    payload = {
        "metadata": {"jobId": "b15-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1}],
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) == 1
    # Mind. der Mandatory-Bonus muss enthalten sein (100.000 pro Slot)
    assert result["metrics"]["totalObjectiveScore"] >= 100000


# ---------------------------------------------------------------------------
# B9: Sonntags-/Feiertagsschonung ohne stille Abschwächung
# ---------------------------------------------------------------------------


def test_sunday_quota_uses_all_sundays_in_period():
    """Sonntage ohne Requirements zaehlen in die Quote (B9): 4 Sonntage im Zeitraum, minFree=26 -> 2 erlaubt."""
    payload = {
        "metadata": {"jobId": "b9-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-25", "minFreeSundaysPerYear": 26},
        "shiftTemplates": [FRUEH],
        "requirements": [
            {"date": "2026-01-04", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-11", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [_emp("emp_001", skills=["Apotheker"], contractHours=60.0)],
        "wishes": [],
    }
    result = _run(payload)
    # 4 Sonntage (4./11./18./25.) im Zeitraum, floor(4*26/52)=2 erlaubt -> beide planbar
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) == 2


def test_sunday_quota_min_free_52_forbids_all_sunday_work():
    """minFreeSundaysPerYear=52 (alle Sonntage frei) darf Sonntagsarbeit nie erlauben (B9)."""
    payload = {
        "metadata": {"jobId": "b9-b"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "minFreeSundaysPerYear": 52},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-04", "shiftId": "S_FRUEH", "count": 1}],
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] == "INFEASIBLE"


def test_sunday_quota_per_employee_stricter_via_ytd():
    """protectedDaysWorkedYTD verbraucht das Sonntagskontingent (§ 11 Abs. 1 ArbZG)."""
    base = {
        "metadata": {"jobId": "b9-c"},
        "config": {"startDate": "2026-02-02", "endDate": "2026-03-29", "minFreeSundaysPerYear": 15},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-02-08", "shiftId": "S_FRUEH", "count": 1}],
        "wishes": [],
    }
    # 8 Sonntage im Zeitraum -> round_half_up(8*37/52)=6 erlaubt
    ok = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"])]))
    assert ok["metadata"]["status"] in ("SUCCESS", "FEASIBLE")

    # YTD=6 verbraucht das Kontingent komplett -> INFEASIBLE
    exhausted = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], protectedDaysWorkedYTD=6)]))
    assert exhausted["metadata"]["status"] == "INFEASIBLE"


# ---------------------------------------------------------------------------
# § 11 Abs. 3 ArbZG: Ersatzruhetag nach Sonn-/Feiertagsarbeit
# ---------------------------------------------------------------------------


def test_ersatz_rest_day_after_sunday_work():
    """Sonntagsarbeit erfordert einen freien Tag binnen 2 Wochen (§ 11 Abs. 3)."""
    base = {
        "metadata": {"jobId": "ersatz-a"},
        "config": {
            "startDate": "2026-01-04",
            "endDate": "2026-01-18",
            "minFreeSundaysPerYear": 0,
            "maxConsecutiveDays": 15,
            "maxWeeklyHoursLaw": 60,
            "minRestTimeHours": 11,
        },
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": f"2026-01-{d:02d}", "shiftId": "S_FRUEH", "count": 1} for d in range(4, 19)],
        "wishes": [],
    }
    # 1 MA: 15 Tage durchgehend Requirements, Sonntag (04.01.) dabei -> der MA
    # muesste im Fenster (04.01., 18.01.] mindestens einen Tag frei haben ->
    # ein mandatory-Requirement bleibt ungedeckt -> INFEASIBLE
    one = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], contractHours=60.0)]))
    assert one["metadata"]["status"] == "INFEASIBLE"

    # 2 MA: feasible (freier Tag im Fenster kann durch den anderen MA abgedeckt werden)
    two = _run(
        dict(
            base,
            employees=[
                _emp("emp_001", skills=["Apotheker"], contractHours=60.0),
                _emp("emp_002", skills=["Apotheker"], contractHours=60.0),
            ],
        )
    )
    assert two["metadata"]["status"] in ("SUCCESS", "FEASIBLE")


def test_ersatz_window_is_14_days_for_sundays_and_56_for_holidays():
    """Fensterlaengen: 14 Tage nach Sonntagsarbeit, 56 Tage nach Feiertagsarbeit auf Werktag."""
    from tito.solver import _ersatz_window_days

    assert _ersatz_window_days("2026-01-04", is_sunday=True, is_holiday=False) == 14
    assert _ersatz_window_days("2026-01-04", is_sunday=True, is_holiday=True) == 14  # Feiertag faellt auf Sonntag
    assert _ersatz_window_days("2026-01-01", is_sunday=False, is_holiday=True) == 56  # Werktag-Feiertag
    assert _ersatz_window_days("2026-01-02", is_sunday=False, is_holiday=False) == 0  # normaler Werktag


# ---------------------------------------------------------------------------
# § 6 ArbZG: Nachtarbeit
# ---------------------------------------------------------------------------


def test_night_worker_capped_at_10_hours():
    """Nachtarbeitnehmer duerfen an Nachtschichten max. nightWorkMaxHours arbeiten (§ 6 Abs. 2)."""
    nacht_lang = {"id": "S_NACHT_LANG", "startTime": "22:00", "endTime": "09:00"}  # 11h brutto, 10.25 netto
    base = {
        "metadata": {"jobId": "night-a"},
        "config": {
            "startDate": "2026-01-01",
            "endDate": "2026-01-07",
            "maxDailyWorkHours": 12,
            "nightWindowStart": "23:00",
            "nightWindowEnd": "06:00",
        },
        "shiftTemplates": [nacht_lang],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_NACHT_LANG", "count": 1}],
        "wishes": [],
    }
    night_worker = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isNightWorker=True)]))
    assert night_worker["metadata"]["status"] == "INFEASIBLE", "11h-Nachtschicht fuer Nachtarbeitnehmer > 10h"

    regular = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isNightWorker=False)]))
    assert regular["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert regular["solution"]["assignments"][0]["isNightShift"] is True


def test_night_flag_set_in_assignments():
    """Assignments kennzeichnen Nachtschichten (isNightShift)."""
    payload = {
        "metadata": {"jobId": "night-b"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH, NACHT],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_NACHT", "count": 1},
        ],
        "employees": [_emp("emp_001", skills=["Apotheker"]), _emp("emp_002", skills=["Apotheker"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    by_shift = {a["shiftId"]: a for a in result["solution"]["assignments"]}
    assert by_shift["S_FRUEH"]["isNightShift"] is False
    assert by_shift["S_NACHT"]["isNightShift"] is True


def test_night_worker_exam_warning():
    """Fehlende/veraltete Eignungsuntersuchung wird als SOFT-Verletzung gemeldet (§ 6 Abs. 1)."""
    base = {
        "metadata": {"jobId": "night-c"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [NACHT],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_NACHT", "count": 1}],
        "wishes": [],
    }
    ohne = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isNightWorker=True)]))
    assert ohne["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    viol_types = {v["type"] for v in ohne["metrics"]["violations"]}
    assert "NIGHT_WORKER_EXAM" in viol_types

    veraltet = _run(
        dict(
            base,
            employees=[_emp("emp_001", skills=["Apotheker"], isNightWorker=True, nightWorkerExamDate="2024-06-01")],
        )
    )
    viol_types = {v["type"] for v in veraltet["metrics"]["violations"]}
    assert "NIGHT_WORKER_EXAM" in viol_types

    aktuell = _run(
        dict(
            base,
            employees=[_emp("emp_001", skills=["Apotheker"], isNightWorker=True, nightWorkerExamDate="2025-12-01")],
        )
    )
    viol_types = {v["type"] for v in aktuell["metrics"]["violations"]}
    assert "NIGHT_WORKER_EXAM" not in viol_types


# ---------------------------------------------------------------------------
# § 21 ArbZG: verkuerzte Ruhezeit fuer Schichtarbeiter
# ---------------------------------------------------------------------------


def test_shift_worker_shortened_rest_time():
    """isShiftWorker + restTimeShiftWorkersHours=9 erlaubt 9h-Ruhe; normale MA brauchen 11h (§ 21)."""
    spaet_23 = {"id": "S_SPAET23", "startTime": "14:00", "endTime": "23:00"}
    frueh_8 = {"id": "S_FRUEH8", "startTime": "08:00", "endTime": "16:00"}
    base = {
        "metadata": {"jobId": "s21-a"},
        "config": {
            "startDate": "2026-01-01",
            "endDate": "2026-01-07",
            "minRestTimeHours": 11,
            "restTimeShiftWorkersHours": 9,
        },
        "shiftTemplates": [spaet_23, frueh_8],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_SPAET23", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_FRUEH8", "count": 1},
        ],
        "wishes": [],
    }
    adult = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isShiftWorker=False)]))
    assert adult["metadata"]["status"] == "INFEASIBLE", "9h Ruhe reichen fuer normale MA nicht"

    shift_worker = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isShiftWorker=True)]))
    assert shift_worker["metadata"]["status"] in ("SUCCESS", "FEASIBLE")


# ---------------------------------------------------------------------------
# JArbSchG (§ 18 Abs. 2 ArbZG): Kernregeln fuer minderjaehrige MA
# ---------------------------------------------------------------------------


def test_minor_requires_12_hours_rest():
    """Minderjaehrige brauchen 12h Ruhezeit (JArbSchG § 16); 11h reichen nicht."""
    spaet_20 = {"id": "S_SPAET20", "startTime": "12:00", "endTime": "20:00"}
    frueh_7 = {"id": "S_FRUEH7", "startTime": "07:00", "endTime": "15:00"}
    base = {
        "metadata": {"jobId": "minor-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "minRestTimeHours": 11},
        "shiftTemplates": [spaet_20, frueh_7],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_SPAET20", "count": 1},
            {"date": "2026-01-03", "shiftId": "S_FRUEH7", "count": 1},
        ],
        "wishes": [],
    }
    adult = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isMinor=False)]))
    assert adult["metadata"]["status"] in ("SUCCESS", "FEASIBLE"), "11h Ruhe genuegt fuer Erwachsene"

    minor = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isMinor=True)]))
    assert minor["metadata"]["status"] == "INFEASIBLE", "Minderjaehrige benoetigen 12h Ruhe"


def test_minor_no_night_work():
    """Minderjaehrige duerfen nicht zwischen 20:00 und 06:00 arbeiten (JArbSchG § 14)."""
    abend = {"id": "S_ABEND19", "startTime": "19:00", "endTime": "23:00"}
    base = {
        "metadata": {"jobId": "minor-b"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [abend],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_ABEND19", "count": 1}],
        "wishes": [],
    }
    minor = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isMinor=True)]))
    assert minor["metadata"]["status"] == "INFEASIBLE"

    adult = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isMinor=False)]))
    assert adult["metadata"]["status"] in ("SUCCESS", "FEASIBLE")


def test_minor_max_8_hours_daily():
    """Minderjaehrige: max. 8h taeglich (JArbSchG § 8); 8.5h netto verboten."""
    lang = {"id": "S_LANG9", "startTime": "06:00", "endTime": "15:00"}  # 9h brutto -> 8.5h netto
    base = {
        "metadata": {"jobId": "minor-c"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "maxDailyWorkHours": 10},
        "shiftTemplates": [lang],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_LANG9", "count": 1}],
        "wishes": [],
    }
    minor = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isMinor=True)]))
    assert minor["metadata"]["status"] == "INFEASIBLE"

    adult = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isMinor=False)]))
    assert adult["metadata"]["status"] in ("SUCCESS", "FEASIBLE")


def test_minor_no_weekend_work():
    """Minderjaehrige arbeiten nicht an Samstagen (JArbSchG § 17 Kernregel, vereinfacht)."""
    base = {
        "metadata": {"jobId": "minor-d"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1}],  # Samstag
        "wishes": [],
    }
    minor = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isMinor=True)]))
    assert minor["metadata"]["status"] == "INFEASIBLE"

    adult = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], isMinor=False)]))
    assert adult["metadata"]["status"] in ("SUCCESS", "FEASIBLE")


# ---------------------------------------------------------------------------
# MuSchG: Beschaeftigungsverbot bis protectionUntil
# ---------------------------------------------------------------------------


def test_protection_until_blocks_assignment():
    """protectionUntil sperrt Zuweisungen bis einschliesslich des Datums (MuSchG)."""
    base = {
        "metadata": {"jobId": "muschg-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1}],
        "wishes": [],
    }
    geschuetzt = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], protectionUntil="2026-01-03")]))
    assert geschuetzt["metadata"]["status"] == "INFEASIBLE"

    zwei = _run(
        dict(
            base,
            employees=[
                _emp("emp_001", skills=["Apotheker"], protectionUntil="2026-01-03"),
                _emp("emp_002", skills=["Apotheker"]),
            ],
        )
    )
    assert zwei["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert {a["employeeId"] for a in zwei["solution"]["assignments"]} == {"emp_002"}


# ---------------------------------------------------------------------------
# C1/C6: Ueberlappende Schichten verboten, Teilschichten (Split-Shifts) erlaubt
# ---------------------------------------------------------------------------


def test_overlapping_shifts_forbidden_even_without_rest_time():
    """Ueberlappende Schichten sind immer verboten - auch bei minRestTimeHours=0 (C1)."""
    template_b = {"id": "S_B", "startTime": "12:00", "endTime": "20:00"}  # ueberlappt FRUEH (06-14) um 2h
    payload = {
        "metadata": {"jobId": "c1-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "minRestTimeHours": 0, "maxDailyWorkHours": 20},
        "shiftTemplates": [FRUEH, template_b],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_B", "count": 1},
        ],
        "employees": [_emp("emp_001", skills=["Apotheker"], contractHours=60.0)],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] == "INFEASIBLE", "Ueberlappende Schichten muessen verboten bleiben"


def test_split_shifts_same_day_allowed():
    """Teilschichten am selben Arbeitstag sind erlaubt; Ruhezeit gilt erst danach (Split-Shifts, C6)."""
    morgen = {"id": "S_MO", "startTime": "06:00", "endTime": "10:00"}
    nachmittag = {"id": "S_MI", "startTime": "14:00", "endTime": "18:00"}
    payload = {
        "metadata": {"jobId": "c6-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "minRestTimeHours": 11},
        "shiftTemplates": [morgen, nachmittag],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_MO", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_MI", "count": 1},
        ],
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) == 2


def test_combined_daily_break_over_six_hours():
    """Pausenpflicht gilt kumulativ fuer den Arbeitstag: 4x3h Teilschichten = 12h brutto -> 45min Pause -> 11.25h netto > 10h (§ 4)."""
    p1 = {"id": "S_P1", "startTime": "08:00", "endTime": "11:00"}
    p2 = {"id": "S_P2", "startTime": "12:00", "endTime": "15:00"}
    p3 = {"id": "S_P3", "startTime": "16:00", "endTime": "19:00"}
    p4 = {"id": "S_P4", "startTime": "20:00", "endTime": "23:00"}
    base = {
        "metadata": {"jobId": "c-pause"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "minRestTimeHours": 0, "maxDailyWorkHours": 10},
        "employees": [_emp("emp_001", skills=["Apotheker"], contractHours=60.0)],
        "wishes": [],
    }
    drei = dict(
        base,
        shiftTemplates=[p1, p2, p3],
        requirements=[
            {"date": "2026-01-02", "shiftId": "S_P1", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_P2", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_P3", "count": 1},
        ],
    )
    result3 = _run(drei)
    # 9h brutto -> 45min gesetzliche Pause -> 8.25h netto <= 10h -> zulassen
    assert result3["metadata"]["status"] in ("SUCCESS", "FEASIBLE")

    vier = dict(
        base,
        shiftTemplates=[p1, p2, p3, p4],
        requirements=[
            {"date": "2026-01-02", "shiftId": "S_P1", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_P2", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_P3", "count": 1},
            {"date": "2026-01-02", "shiftId": "S_P4", "count": 1},
        ],
    )
    result4 = _run(vier)
    # 12h brutto -> 45min Pause -> 11.25h netto > 10h -> verboten
    assert result4["metadata"]["status"] == "INFEASIBLE"


def test_break_thresholds_exactly_six_and_nine_hours():
    """§ 4 ArbZG Grenzwerte exakt: Pause erst bei MEHR als 6h bzw. 9h (C10)."""
    genau6 = {"id": "S_G6", "startTime": "06:00", "endTime": "12:00"}  # exakt 6h -> keine Pause
    mehr6 = {"id": "S_M6", "startTime": "06:00", "endTime": "12:05"}  # 6h05 -> 30min Pause
    base = {
        "metadata": {"jobId": "c10-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [],
    }
    # maxDaily=5.6h: exakt 6h netto (keine Pause) -> 6h > 5.6h -> INFEASIBLE
    genau = _run(
        dict(
            base,
            config={"startDate": "2026-01-01", "endDate": "2026-01-07", "maxDailyWorkHours": 5.6},
            shiftTemplates=[genau6],
            requirements=[{"date": "2026-01-02", "shiftId": "S_G6", "count": 1}],
        )
    )
    assert genau["metadata"]["status"] == "INFEASIBLE"

    # 6h05 - 30min Pause = 5h35 netto <= 5.6h -> zulassen
    mehr = _run(
        dict(
            base,
            config={"startDate": "2026-01-01", "endDate": "2026-01-07", "maxDailyWorkHours": 5.6},
            shiftTemplates=[mehr6],
            requirements=[{"date": "2026-01-02", "shiftId": "S_M6", "count": 1}],
        )
    )
    assert mehr["metadata"]["status"] in ("SUCCESS", "FEASIBLE")

    # 9h-Grenze: exakt 9h -> 30min Pause (510 netto); 9h01 -> 45min (496 netto)
    genau9 = {"id": "S_G9", "startTime": "06:00", "endTime": "15:00"}
    mehr9 = {"id": "S_M9", "startTime": "06:00", "endTime": "15:01"}
    neun = _run(
        dict(
            base,
            config={"startDate": "2026-01-01", "endDate": "2026-01-07", "maxDailyWorkHours": 505 / 60},
            shiftTemplates=[genau9],
            requirements=[{"date": "2026-01-02", "shiftId": "S_G9", "count": 1}],
        )
    )
    assert neun["metadata"]["status"] == "INFEASIBLE", "exakt 9h -> nur 30min Pause -> 510min netto > 505"

    neunmehr = _run(
        dict(
            base,
            config={"startDate": "2026-01-01", "endDate": "2026-01-07", "maxDailyWorkHours": 505 / 60},
            shiftTemplates=[mehr9],
            requirements=[{"date": "2026-01-02", "shiftId": "S_M9", "count": 1}],
        )
    )
    assert neunmehr["metadata"]["status"] in ("SUCCESS", "FEASIBLE"), "9h01 -> 45min Pause -> 496min netto <= 505"


# ---------------------------------------------------------------------------
# C3: Multi-Skill-Requirements expandieren pro Skill
# ---------------------------------------------------------------------------


def test_multi_skill_requirement_expands_per_skill():
    """neededSkills {A:1, B:1} bedeutet einen A-MA UND einen B-MA - nicht zwei MA mit A und B (C3)."""
    payload = {
        "metadata": {"jobId": "c3-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "neededSkills": {"A": 1, "B": 1}}],
        "employees": [_emp("emp_001", skills=["A"]), _emp("emp_002", skills=["B"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assigned = {a["employeeId"] for a in result["solution"]["assignments"]}
    assert assigned == {"emp_001", "emp_002"}


# ---------------------------------------------------------------------------
# C2: PREFER_SHIFT erfuellt sich ueber jeden Slot der Schichtgruppe
# ---------------------------------------------------------------------------


def test_prefer_shift_fulfilled_on_any_slot_of_group():
    """PREFER_SHIFT zaehlt als erfuellt, wenn der MA irgendeinen Slot der (date, shift)-Gruppe erhaelt (C2)."""
    payload = {
        "metadata": {"jobId": "c2-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 2}],
        "employees": [_emp("emp_001", skills=["Apotheker"]), _emp("emp_002", skills=["Apotheker"])],
        "wishes": [
            {"employeeId": "emp_001", "type": "PREFER_SHIFT", "shiftId": "S_FRUEH", "date": "2026-01-02", "priority": 9}
        ],
    }
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert result["metrics"]["wishFulfillmentRate"] == 100.0
    emp1_dates = [a for a in result["solution"]["assignments"] if a["employeeId"] == "emp_001"]
    assert len(emp1_dates) == 1


def test_wish_without_matching_requirement_reported_not_applicable():
    """PREFER_SHIFT ohne passendes Requirement wird als WISH_NOT_APPLICABLE gemeldet und nicht in die Rate gezaehlt (B14)."""
    payload = {
        "metadata": {"jobId": "c2-b"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1}],
        "employees": [_emp("emp_001", skills=["Apotheker"]), _emp("emp_002", skills=["Apotheker"])],
        "wishes": [
            {"employeeId": "emp_001", "type": "PREFER_SHIFT", "shiftId": "S_FRUEH", "date": "2026-01-06", "priority": 5}
        ],
    }
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    viol_types = {v["type"] for v in result["metrics"]["violations"]}
    assert "WISH_NOT_APPLICABLE" in viol_types
    # Nicht erfuellbarer PREFER-Wunsch zaehlt konsistent als nicht erfuellt (B14,
    # deckungsgleich mit dem Leerlauf-Vertrag "preferred without requirements -> 0.0")
    assert result["metrics"]["wishFulfillmentRate"] == 0.0


# ---------------------------------------------------------------------------
# B10: maxConsecutiveDays ueber echte Kalendertage (Luecken unterbrechen Ketten)
# ---------------------------------------------------------------------------


def test_consecutive_days_chain_broken_by_weekend():
    """Ein freies Wochenende unterbricht die Kette - 5 Werktage + 2 Werktage sind keine 7 Folgetage (B10)."""
    payload = {
        "metadata": {"jobId": "b10-a"},
        "config": {"startDate": "2026-01-05", "endDate": "2026-01-13", "maxConsecutiveDays": 6},
        "shiftTemplates": [FRUEH],
        "requirements": [
            {"date": "2026-01-05", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-06", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-07", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-08", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-09", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-12", "shiftId": "S_FRUEH", "count": 1},
            {"date": "2026-01-13", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [_emp("emp_001", skills=["Apotheker"], contractHours=60.0)],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE"), (
        "Kette Mo-Fr (5) + Mo-Di (2) darf maxConsecutiveDays=6 nicht verletzen (Wochenende unterbricht)"
    )
    assert len(result["solution"]["assignments"]) == 7


# ---------------------------------------------------------------------------
# § 3 ArbZG: gesetzliche Wochenobergrenze
# ---------------------------------------------------------------------------


def test_weekly_law_cap_48_hours():
    """7 Schichten in einer ISO-Woche (52.5h netto) verletzen die 48h-Obergrenze (§ 3)."""
    base = {
        "metadata": {"jobId": "wlaw-a"},
        "config": {
            "startDate": "2026-01-05",
            "endDate": "2026-01-11",
            "minFreeSundaysPerYear": 0,
            "maxConsecutiveDays": 7,
        },
        "shiftTemplates": [FRUEH],
        "employees": [_emp("emp_001", skills=["Apotheker"], contractHours=60.0)],
        "wishes": [],
    }
    sieben_tage = _run(
        dict(
            base,
            requirements=[{"date": f"2026-01-{d:02d}", "shiftId": "S_FRUEH", "count": 1} for d in range(5, 12)],
        )
    )
    assert sieben_tage["metadata"]["status"] == "INFEASIBLE", "7x7.5h netto = 52.5h > 48h Gesetzesgrenze"

    sechs_tage = _run(
        dict(
            base,
            requirements=[{"date": f"2026-01-{d:02d}", "shiftId": "S_FRUEH", "count": 1} for d in range(5, 11)],
        )
    )
    assert sechs_tage["metadata"]["status"] in ("SUCCESS", "FEASIBLE")


# ---------------------------------------------------------------------------
# C8: preShifts - Vorperioden und planuebergreifende Schichten
# ---------------------------------------------------------------------------


def test_pre_shifts_enforce_rest_time():
    """Eine fixe Vorschicht begrenzt die frueheste Folgeschicht per Ruhezeit (C8)."""
    frueh_9 = {"id": "S_FRUEH9", "startTime": "09:00", "endTime": "17:00"}
    base = {
        "metadata": {"jobId": "c8-a"},
        "config": {"startDate": "2026-01-02", "endDate": "2026-01-03", "minRestTimeHours": 11},
        "shiftTemplates": [FRUEH, frueh_9],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 1}],
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [],
        "preShifts": [{"employeeId": "emp_001", "date": "2026-01-01", "startTime": "14:00", "endTime": "22:00"}],
    }
    # FRUEH ab 06:00 -> nur 8h Ruhe zur Vorschicht -> INFEASIBLE
    result = _run(base)
    assert result["metadata"]["status"] == "INFEASIBLE"

    # Schicht ab 09:00 -> 11h Ruhe -> zulassen
    result_ok = _run(dict(base, requirements=[{"date": "2026-01-02", "shiftId": "S_FRUEH9", "count": 1}]))
    assert result_ok["metadata"]["status"] in ("SUCCESS", "FEASIBLE")


def test_pre_shifts_count_toward_weekly_hours():
    """preShifts zaehlen zur Wochenstunden-Bilanz derselben ISO-Woche (C8)."""
    payload = {
        "metadata": {"jobId": "c8-b"},
        "config": {"startDate": "2026-01-08", "endDate": "2026-01-11"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-08", "shiftId": "S_FRUEH", "count": 1}],
        "employees": [_emp("emp_001", skills=["Apotheker"], contractHours=28.0)],
        "wishes": [],
        "preShifts": [
            {"employeeId": "emp_001", "date": "2026-01-05", "startTime": "06:00", "endTime": "14:00"},
            {"employeeId": "emp_001", "date": "2026-01-06", "startTime": "06:00", "endTime": "14:00"},
            {"employeeId": "emp_001", "date": "2026-01-07", "startTime": "06:00", "endTime": "14:00"},
        ],
    }
    result = _run(payload)
    # 3 Vorschichten (22.5h netto) + 7.5h = 30h > 28h Vertrag -> INFEASIBLE
    assert result["metadata"]["status"] == "INFEASIBLE"

    ohne = _run(dict(payload, preShifts=None))
    assert ohne["metadata"]["status"] in ("SUCCESS", "FEASIBLE")


# ---------------------------------------------------------------------------
# D3: Per-Mitarbeiter-Limits
# ---------------------------------------------------------------------------


def test_per_employee_daily_hours_limit():
    """employee.maxDailyHours ist strenger als die Config (D3)."""
    lang9 = {"id": "S_L9", "startTime": "06:00", "endTime": "15:00"}  # 9h brutto -> 8.5h netto
    base = {
        "metadata": {"jobId": "d3-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "maxDailyWorkHours": 10},
        "shiftTemplates": [lang9],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_L9", "count": 1}],
        "wishes": [],
    }
    begrenzt = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], maxDailyHours=8)]))
    assert begrenzt["metadata"]["status"] == "INFEASIBLE", "8.5h netto > individuelles 8h-Limit"

    unbegrenzt = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"])]))
    assert unbegrenzt["metadata"]["status"] in ("SUCCESS", "FEASIBLE")


def test_per_employee_min_free_sundays_stricter():
    """employee.minFreeSundaysPerYear ist strenger als die Config (D3)."""
    base = {
        "metadata": {"jobId": "d3-b"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-25", "minFreeSundaysPerYear": 15},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-04", "shiftId": "S_FRUEH", "count": 1}],
        "wishes": [],
    }
    # 4 Sonntage im Zeitraum: config minFree=15 -> round_half_up(4*37/52)=3 erlaubt
    locker = _run(dict(base, employees=[_emp("emp_001", skills=["Apotheker"], contractHours=60.0)]))
    assert locker["metadata"]["status"] in ("SUCCESS", "FEASIBLE")

    # individuell minFree=46 -> round_half_up(4*6/52)=0 erlaubt -> INFEASIBLE
    streng = _run(
        dict(base, employees=[_emp("emp_001", skills=["Apotheker"], contractHours=60.0, minFreeSundaysPerYear=46)])
    )
    assert streng["metadata"]["status"] == "INFEASIBLE"


# ---------------------------------------------------------------------------
# D4: Requirement-Zeit-Overrides
# ---------------------------------------------------------------------------


def test_requirement_time_overrides_respected():
    """Requirement.startTime/endTime ueberschreiben das Template und steuern Ruhezeit/Dauer (D4)."""
    base = {
        "metadata": {"jobId": "d4-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07", "minRestTimeHours": 11},
        "shiftTemplates": [SPAET, FRUEH],
        "requirements": [
            {"date": "2026-01-02", "shiftId": "S_SPAET", "count": 1, "endTime": "19:00"},
            {"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1},
        ],
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [],
    }
    # Override 14:00-19:00 -> Ruhe bis 06:00 = 11h -> zulassen
    result = _run(base)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    spaet = next(a for a in result["solution"]["assignments"] if a["shiftId"] == "S_SPAET")
    assert spaet["endTime"] == "19:00", "Override-Zeit muss im Assignment stehen"
    # 14:00-19:00 = 5h, law break 0 -> 5.0h netto; FRUEH 8h -> 7.5h netto
    assert result["metrics"]["employeeUtilization"]["emp_001"] == 12.5

    # Ohne Override endet die Spaetschicht 22:00 -> nur 8h Ruhe -> INFEASIBLE
    ohne = _run(
        dict(
            base,
            requirements=[
                {"date": "2026-01-02", "shiftId": "S_SPAET", "count": 1},
                {"date": "2026-01-03", "shiftId": "S_FRUEH", "count": 1},
            ],
        )
    )
    assert ohne["metadata"]["status"] == "INFEASIBLE"


# ---------------------------------------------------------------------------
# D5: ShiftTemplate.skills als Fallback
# ---------------------------------------------------------------------------


def test_template_skills_used_when_requirement_has_none():
    """Requirements ohne eigene Skills erben die Skills des Templates (D5)."""
    template = {"id": "S_SKILL", "startTime": "06:00", "endTime": "14:00", "skills": ["A"]}
    base = {
        "metadata": {"jobId": "d5-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [template],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_SKILL", "count": 1}],
        "wishes": [],
    }
    ohne_skill = _run(dict(base, employees=[_emp("emp_001", skills=["B"])]))
    assert ohne_skill["metadata"]["status"] == "INFEASIBLE"

    mit_skill = _run(dict(base, employees=[_emp("emp_002", skills=["A"])]))
    assert mit_skill["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert mit_skill["solution"]["assignments"][0]["employeeId"] == "emp_002"


# ---------------------------------------------------------------------------
# D6: INFEASIBLE-Diagnose
# ---------------------------------------------------------------------------


def test_infeasible_diagnosis_reports_skill_coverage():
    """Bei INFEASIBLE nennt diagnostics.infeasibilityReasons die Ursache (D6)."""
    payload = {
        "metadata": {"jobId": "d6-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "neededSkills": {"Chirurg": 1}}],
        "employees": [_emp("emp_001", skills=["Apotheker"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] == "INFEASIBLE"
    reasons = result["diagnostics"]["infeasibilityReasons"]
    assert reasons, "INFEASIBLE ohne Diagnose ist nicht akzeptabel"
    assert any("Chirurg" in r or "skill" in r.lower() or "qualif" in r.lower() for r in reasons)


# ---------------------------------------------------------------------------
# D7: unassignedRequirements originalgetreu
# ---------------------------------------------------------------------------


def test_unassigned_requirements_aggregated_per_original():
    """unassignedRequirements referenzieren das Original-Requirement mit missingCount statt expandierter Slots (D7)."""
    payload = {
        "metadata": {"jobId": "d7-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_FRUEH", "count": 2, "maxCount": 3}],
        "employees": [_emp("emp_001", skills=["Apotheker"]), _emp("emp_002", skills=["Apotheker"])],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    assert len(result["solution"]["assignments"]) == 2
    unassigned = result["solution"]["unassignedRequirements"]
    assert len(unassigned) == 1
    assert unassigned[0]["missingCount"] == 1
    soft = [v for v in result["metrics"]["violations"] if v["type"] == "UNASSIGNED_REQUIREMENT"]
    assert len(soft) == 1
    assert soft[0]["severity"] == "SOFT"


# ---------------------------------------------------------------------------
# C9: Determinismus
# ---------------------------------------------------------------------------


def test_deterministic_with_single_worker_and_seed():
    """numSearchWorkers=1 + randomSeed liefern reproduzierbare Ergebnisse (C9)."""
    payload = {
        "metadata": {"jobId": "c9-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-14", "numSearchWorkers": 1, "randomSeed": 7},
        "shiftTemplates": [FRUEH, SPAET],
        "requirements": [{"date": f"2026-01-{d:02d}", "shiftId": "S_FRUEH", "count": 1} for d in range(2, 10)]
        + [{"date": "2026-01-09", "shiftId": "S_SPAET", "count": 1}],
        "employees": [
            _emp("emp_001", skills=["Apotheker"]),
            _emp("emp_002", skills=["Apotheker"]),
            _emp("emp_003", skills=["Apotheker"]),
        ],
        "wishes": [],
    }
    r1 = _run(payload)
    r2 = _run(payload)
    key = lambda r: sorted((a["employeeId"], a["date"], a["shiftId"]) for a in r["solution"]["assignments"])
    assert key(r1) == key(r2)


# ---------------------------------------------------------------------------
# B17/B18: build_model-Validierung (Dict-Pfad)
# ---------------------------------------------------------------------------


def test_build_model_rejects_invalid_payloads():
    """build_model validiert den Dict-Pfad frueh und mit klarer Meldung (B17/B18)."""
    base = {
        "metadata": {"jobId": "b17"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [FRUEH],
        "employees": [_emp("emp_001")],
        "wishes": [],
    }
    # Requirement ohne date (B18)
    with pytest.raises(ValueError, match="date"):
        build_model(dict(base, requirements=[{"shiftId": "S_FRUEH", "count": 1}]))

    # Requirement mit unbekannter Schicht (B17)
    with pytest.raises(ValueError, match="shift"):
        build_model(dict(base, requirements=[{"date": "2026-01-02", "shiftId": "UNKNOWN", "count": 1}]))

    # Doppelte Template-IDs (B17)
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        build_model(dict(base, shiftTemplates=[FRUEH, dict(FRUEH)], requirements=[]))

    # Requirement ausserhalb des Planungszeitraums (C7)
    with pytest.raises(ValueError, match="outside"):
        build_model(dict(base, requirements=[{"date": "2026-02-01", "shiftId": "S_FRUEH", "count": 1}]))

    # Template ohne id (B17)
    with pytest.raises(ValueError, match="id"):
        build_model(dict(base, shiftTemplates=[{"startTime": "06:00", "endTime": "14:00"}], requirements=[]))


def test_break_minutes_recommended_in_assignments():
    """Assignments empfehlen die gesetzliche/vertragliche Pause als breakMinutes (§ 4)."""
    template = {"id": "S_8H", "startTime": "06:00", "endTime": "14:00", "minBreakMinutes": 20}
    payload = {
        "metadata": {"jobId": "break-a"},
        "config": {"startDate": "2026-01-01", "endDate": "2026-01-07"},
        "shiftTemplates": [template],
        "requirements": [{"date": "2026-01-02", "shiftId": "S_8H", "count": 1}],
        "employees": [_emp("emp_001", skills=["Apotheker"], breakMinutes=25)],
        "wishes": [],
    }
    result = _run(payload)
    assert result["metadata"]["status"] in ("SUCCESS", "FEASIBLE")
    a = result["solution"]["assignments"][0]
    # max(30 gesetzlich, 20 Template, 25 Mitarbeiter) = 30
    assert a["breakMinutes"] == 30
