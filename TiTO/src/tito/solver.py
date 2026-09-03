"""TiTO Duty-Scheduling Solver (Google OR-Tools CP-SAT).

Enthält das Arbeitsrecht-Regelwerk als harte Constraints:

- § 3 ArbZG   max. Tagesarbeitszeit (Netto, Pausen zählen nicht zur Arbeitszeit, § 2 Abs. 1)
              und gesetzliche Wochenobergrenze (48h-Durchschnitt, konservativ als Wochen-Cap)
- § 4 ArbZG   Ruhepausen (>6h: 30 min, >9h: 45 min) - kumulativ pro Arbeitstag
- § 5 ArbZG   11h ununterbrochene Ruhezeit zwischen Arbeitstagen (absolute Zeitstempel,
              korrekt für Mitternacht überschreitende Schichten)
- § 6 ArbZG   Nachtarbeit: 10h-Deckel für Nachtarbeitnehmer, Eignungsuntersuchung (SOFT)
- § 9/§ 11   Sonn-/Feiertagsschonung: Jahreskontingent (pro-rata + YTD-Saldo) und
              Ersatzruhetag binnen 2 Wochen (Sonntag) / 8 Wochen (Feiertag auf Werktag)
- § 21 ArbZG  verkürzte Ruhezeit für Schichtarbeiter (konfigurierbar, mind. 9h)
- § 18 Abs. 2 ArbZG -> JArbSchG-Kernregeln für Minderjährige (12h Ruhe, 8h/Tag,
              40h/Woche, 5 Werktage, keine Nachtarbeit 20-06 Uhr, kein Sa/So/Feiertag)
- MuSchG      Beschäftigungsverbot bis protectionUntil
- Teilschichten (Split-Shifts): mehrere Schichten am selben Arbeitstag sind zulässig;
              die Ruhezeit (§ 5) gilt zwischen Arbeitstagen, Überlappungen sind stets verboten
"""

import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from ortools.sat.python.cp_model import CpModel, CpSolver, LinearExpr

from .schema import JobPayload

logger = logging.getLogger(__name__)

# Zielfunktionsgewichte (dokumentiert, B8):
# - Mandatory-Zuweisung dominiert alles (100.000 pro Slot)
# - Wunscherfüllung: 2.000 x weight (weight/priority 1-10)
# - Fairness-Abweichung: -50 pro Minute (eine 8h-Umverteilung wiegt 24.000)
# - Optional-Slots: +60 pro Netto-Minute (nur maximizeStaffing; > Fairness-Strafe,
#   damit Aufstockung lohnt)
# - Balance-Recovery: ±1,04 pro Netto-Minute x Zeitkontostand
MANDATORY_BONUS = 100_000
WISH_BONUS_PER_UNIT = 2_000
FAIRNESS_PENALTY_PER_MIN = 50
OPTIONAL_BONUS_PER_MIN = 60
BALANCE_RECOVERY_PER_MIN = 500 / 480

LAW_BREAK_6H = 30
LAW_BREAK_9H_EXTRA = 15
MINOR_REST_MINUTES = 12 * 60
MINOR_MAX_DAILY_MINUTES = 8 * 60
MINOR_MAX_WEEKLY_MINUTES = 40 * 60
MINOR_MAX_WORKDAYS_PER_WEEK = 5
MINOR_NIGHT_START = 20 * 60
MINOR_NIGHT_END = 6 * 60
NIGHT_WORK_MIN_OVERLAP_MINUTES = 120
ERSATZ_WINDOW_SUNDAY_DAYS = 14
ERSATZ_WINDOW_HOLIDAY_DAYS = 56
EXAM_VALIDITY_DAYS = 365

# Constraint-Familien für die INFEASIBLE-Diagnose (D6)
RELAX_FAMILIES = (
    "qualifications",
    "off_wishes",
    "protection",
    "rest_time",
    "daily_max",
    "weekly_hours",
    "protected_days",
    "consecutive_days",
    "shift_rotation",
    "night_rules",
    "minor_rules",
    "ersatz_rest",
)


def _time_to_minutes(time_str: str) -> int:
    hours, minutes = str(time_str).split(":")
    return int(hours) * 60 + int(minutes)


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(str(date_str), "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _date_to_week_key(date_str: str) -> tuple[int, int]:
    year, week, _ = _parse_date(date_str).isocalendar()
    return year, week


def _is_sunday(date_str: str) -> bool:
    return _parse_date(date_str).weekday() == 6


def _is_saturday(date_str: str) -> bool:
    return _parse_date(date_str).weekday() == 5


def _law_break_minutes(brutto_minutes: int) -> int:
    """§ 4 ArbZG: >6h bis 9h -> 30 min, >9h -> 45 min (exakte Grenzwerte, C10)."""
    if brutto_minutes > 9 * 60:
        return LAW_BREAK_6H + LAW_BREAK_9H_EXTRA
    if brutto_minutes > 6 * 60:
        return LAW_BREAK_6H
    return 0


def _recommended_break_minutes(brutto_minutes: int, template_break: int, employee_break: int) -> int:
    return max(_law_break_minutes(brutto_minutes), template_break or 0, employee_break or 0)


def _ersatz_window_days(date_str: str, is_sunday: bool, is_holiday: bool) -> int:
    """§ 11 Abs. 3 ArbZG: Ersatzruhetag binnen 2 Wochen nach Sonntagsarbeit,
    binnen 8 Wochen nach Feiertagsarbeit (Feiertag auf Werktag)."""
    if is_sunday:
        return ERSATZ_WINDOW_SUNDAY_DAYS
    if is_holiday:
        return ERSATZ_WINDOW_HOLIDAY_DAYS
    return 0


def _overlap_with_daily_window(start_abs: int, end_abs: int, window_start: int, window_end: int) -> int:
    """Überlappung (Minuten) eines Intervalls [start_abs, end_abs) mit einem
    täglich wiederkehrenden Fenster [window_start, window_end) (über Mitternacht,
    falls window_end <= window_start)."""
    if end_abs <= start_abs:
        return 0
    span = window_end - window_start
    if span <= 0:
        span += 24 * 60
    overlap = 0
    first_day = start_abs // (24 * 60)
    last_day = (end_abs - 1) // (24 * 60)
    for day in range(first_day, last_day + 1):
        w_start = day * 24 * 60 + window_start
        w_end = w_start + span
        overlap += max(0, min(end_abs, w_end) - max(start_abs, w_start))
        if overlap >= NIGHT_WORK_MIN_OVERLAP_MINUTES:
            break
    return overlap


def _parse_hhmm(value, field: str) -> str:
    if value is None:
        raise ValueError(f"Ungültiges Payload: Feld '{field}' fehlt")
    text = str(value)
    parts = text.split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Ungültiges Zeitformat für '{field}': {value!r} (HH:MM erwartet)")
    return text


def build_model(payload: dict | JobPayload) -> dict:
    """Übersetze das Eingabe-Payload in ein vorläufiges Modell.

    Validiert den Dict-Pfad früh und mit klarer Meldung (B17/B18):
    fehlende/ungültige Requirement-Daten, unbekannte oder doppelte Shift-Template-IDs
    und Requirements außerhalb des Planungszeitraums (C7) werden als ValueError
    gemeldet statt still zu falschen Zeiten zu führen.
    """
    if isinstance(payload, JobPayload):
        payload_dict = payload.model_dump()
    else:
        payload_dict = payload

    templates_raw = payload_dict.get("shiftTemplates") or []
    shift_templates: dict[str, dict] = {}
    for item in templates_raw:
        if not isinstance(item, dict) or not item.get("id"):
            raise ValueError("Jedes ShiftTemplate benötigt ein Feld 'id'")
        template_id = str(item["id"])
        if template_id in shift_templates:
            raise ValueError(f"Duplicate shift template id: {template_id}")
        _parse_hhmm(item.get("startTime"), f"shiftTemplate[{template_id}].startTime")
        _parse_hhmm(item.get("endTime"), f"shiftTemplate[{template_id}].endTime")
        shift_templates[template_id] = item

    config = payload_dict.get("config") or {}
    requirements_raw = payload_dict.get("requirements") or []
    requirements: list[dict] = []
    for index, req in enumerate(requirements_raw):
        if not isinstance(req, dict):
            raise TypeError(f"Requirement #{index} ist kein Objekt")
        date = req.get("date")
        if not date:
            raise ValueError(f"Requirement #{index} benötigt ein Datum ('date')")
        _parse_date(date)
        shift_id = req.get("shiftId") or req.get("shiftTemplateId")
        if not shift_id:
            raise ValueError(f"Requirement #{index} benötigt eine Schicht ('shiftId')")
        if str(shift_id) not in shift_templates:
            raise ValueError(f"Requirement references unknown shift template: {shift_id}")
        requirements.append(req)

    start_date = config.get("startDate")
    end_date = config.get("endDate")
    if start_date and end_date:
        start_dt = _parse_date(start_date)
        end_dt = _parse_date(end_date)
        if start_dt >= end_dt:
            raise ValueError("startDate must be before endDate")
        for req in requirements:
            req_dt = _parse_date(req["date"])
            if req_dt < start_dt or req_dt > end_dt:
                raise ValueError(
                    f"Requirement date {req['date']} is outside the planning period "
                    f"[{start_date}, {end_date}]"
                )

    employees = payload_dict.get("employees") or []
    employee_ids = {e.get("id") for e in employees}
    for pre in payload_dict.get("preShifts") or []:
        if not isinstance(pre, dict) or not pre.get("employeeId"):
            raise ValueError("Jeder preShift benötigt ein Feld 'employeeId'")
        if pre["employeeId"] not in employee_ids:
            raise ValueError(f"PreShift references unknown employee: {pre.get('employeeId')}")
        _parse_date(pre.get("date"))
        _parse_hhmm(pre.get("startTime"), "preShift.startTime")
        _parse_hhmm(pre.get("endTime"), "preShift.endTime")

    return {
        "metadata": payload_dict.get("metadata", {}),
        "config": config,
        "shiftTemplates": shift_templates,
        "requirements": requirements,
        "employees": employees,
        "wishes": payload_dict.get("wishes") or [],
        "preShifts": payload_dict.get("preShifts") or [],
    }


def _extract_employee_float(employee: dict, key: str, default: float, config_default: float) -> float:
    value = employee.get(key)
    if value is None:
        return config_default
    return float(value)


def _emp_contract_hours(employee: dict, default_weekly: float) -> float:
    hours = employee.get("contractHours")
    if hours is None and employee.get("contract"):
        hours = employee["contract"].get("weeklyHours")
    return float(hours) if hours else default_weekly


def _slot_required_skills(req: dict, template: dict) -> list[str]:
    needed = req.get("neededSkills")
    if isinstance(needed, dict) and needed:
        return list(needed.keys())
    skills = req.get("skills")
    if isinstance(skills, list) and skills:
        return [str(s) for s in skills]
    template_skills = template.get("skills")
    if isinstance(template_skills, list) and template_skills:
        return [str(s) for s in template_skills]
    return []


def _role_from_skills(skills: list[str]) -> str | None:
    for skill in skills:
        if skill.startswith("ROLE_"):
            return skill.replace("ROLE_", "", 1)
    return None


def _prepare(model: dict) -> dict:
    """Baut den Lösungs-Kontext: Config, expandierte Slots, Validity-Matrix, preShifts."""
    config = model.get("config") or {}
    employees = list(model.get("employees") or [])
    requirements = list(model.get("requirements") or [])
    wishes = list(model.get("wishes") or [])
    pre_shifts_raw = list(model.get("preShifts") or [])
    shift_templates: dict[str, dict] = model["shiftTemplates"]

    start_str = config.get("startDate")
    end_str = config.get("endDate")
    dates = [r["date"] for r in requirements]
    for pre in pre_shifts_raw:
        dates.append(pre["date"])
    if not start_str:
        start_str = min(dates) if dates else "2026-01-01"
    if not end_str:
        end_str = max(dates) if dates else start_str
    reference = _parse_date(start_str)
    end_dt = _parse_date(end_str)

    def _abs(date_str: str, time_str: str) -> int:
        return (_parse_date(date_str) - reference).days * 1440 + _time_to_minutes(time_str)

    maximize_staffing = bool(config.get("maximizeStaffing", False))

    # --- Slot-Expansion (C3: neededSkills {A:1,B:1} -> ein A-Slot + ein B-Slot) ---
    slots: list[dict] = []
    for orig_index, req in enumerate(requirements):
        template = shift_templates[str(req.get("shiftId") or req.get("shiftTemplateId"))]
        start_str_slot = _parse_hhmm(req.get("startTime") or template.get("startTime"), "startTime")
        end_str_slot = _parse_hhmm(req.get("endTime") or template.get("endTime"), "endTime")
        start_minutes = _time_to_minutes(start_str_slot)
        end_minutes = _time_to_minutes(end_str_slot)
        brutto = end_minutes - start_minutes
        if brutto <= 0:
            brutto += 1440
        start_abs = _abs(req["date"], start_str_slot)
        end_abs = start_abs + brutto

        needed = req.get("neededSkills")
        if isinstance(needed, dict) and needed:
            per_skill = []
            for skill, count in needed.items():
                per_skill.extend([str(skill)] * max(1, int(count)))
            count = req.get("count")
            if count is None:
                count = len(per_skill)
            count = max(1, int(count))
        else:
            skills_list = req.get("skills") or template.get("skills") or []
            count = req.get("count")
            if count is None:
                count = len(skills_list) if isinstance(skills_list, list) and skills_list else 1
            count = max(1, int(count))
            per_skill = [None] * count if not skills_list else None
            if per_skill is None:
                per_skill = [str(s) for s in skills_list] * math.ceil(count / max(1, len(skills_list)))
                per_skill = per_skill[:count]

        max_count = req.get("maxCount")
        if max_count is not None:
            max_count = max(int(max_count), count)

        if maximize_staffing and max_count is None:
            required_skills = _slot_required_skills(req, template)
            role_required = _role_from_skills(required_skills)
            qualified = 0
            for emp in employees:
                emp_skills = set(emp.get("skills") or [])
                if required_skills and not all(s in emp_skills for s in required_skills):
                    continue
                if role_required and emp.get("role") != role_required:
                    continue
                qualified += 1
            max_count = max(count, qualified)

        total_slots = max_count if max_count is not None else count
        for slot_index in range(total_slots):
            skill = per_skill[slot_index % len(per_skill)] if per_skill else None
            slots.append(
                {
                    "orig_index": orig_index,
                    "index": len(slots),
                    "date": req["date"],
                    "shift_id": str(req.get("shiftId") or req.get("shiftTemplateId")),
                    "template": template,
                    "start_abs": start_abs,
                    "end_abs": end_abs,
                    "start_str": start_str_slot,
                    "end_str": end_str_slot,
                    "brutto": brutto,
                    "netto": brutto - _law_break_minutes(brutto),
                    "skill": skill,
                    "required_skills": _slot_required_skills(req, template) if skill is None else [skill],
                    "template_min_break": int(template.get("minBreakMinutes") or 0),
                    "mandatory": slot_index < count,
                    "is_night": False,
                    "group": (req["date"], str(req.get("shiftId") or req.get("shiftTemplateId"))),
                }
            )

    night_ws = _time_to_minutes(_parse_hhmm(config.get("nightWindowStart") or "23:00", "nightWindowStart"))
    night_we = _time_to_minutes(_parse_hhmm(config.get("nightWindowEnd") or "06:00", "nightWindowEnd"))
    for slot in slots:
        if _overlap_with_daily_window(slot["start_abs"], slot["end_abs"], night_ws, night_we) >= NIGHT_WORK_MIN_OVERLAP_MINUTES:
            slot["is_night"] = True

    # --- OFF-/Urlaubs-/Unavailable-Tage aus Wünschen (hart, B1) ---
    off_dates: dict[tuple[str, str], bool] = {}
    for wish in wishes:
        if wish.get("type", "") in ("OFF", "vacation", "unavailable"):
            off_dates[(str(wish.get("employeeId")), str(wish.get("date")))] = True

    # --- protected days: Sonntage + Feiertage im Planungszeitraum (B9: alle, nicht nur req-Tage) ---
    holiday_set = {str(d) for d in (config.get("holidayDates") or [])}
    sunday_set = set()
    saturday_set = set()
    all_days = []
    cursor = reference
    while cursor <= end_dt:
        key = cursor.strftime("%Y-%m-%d")
        all_days.append(key)
        if cursor.weekday() == 6:
            sunday_set.add(key)
        if cursor.weekday() == 5:
            saturday_set.add(key)
        cursor += timedelta(days=1)
    protected_days = sorted(sunday_set | (holiday_set & set(all_days)))

    # --- preShifts pro Mitarbeiter normalisieren (C8) ---
    employee_index = {str(e.get("id")): i for i, e in enumerate(employees)}
    pre_shifts: dict[int, list[dict]] = defaultdict(list)
    for pre in pre_shifts_raw:
        emp_idx = employee_index.get(str(pre.get("employeeId")))
        if emp_idx is None:
            continue
        start_abs = _abs(pre["date"], _parse_hhmm(pre.get("startTime"), "preShift.startTime"))
        end_minutes = _time_to_minutes(_parse_hhmm(pre.get("endTime"), "preShift.endTime"))
        brutto = end_minutes - _time_to_minutes(pre["startTime"])
        if brutto <= 0:
            brutto += 1440
        brutto = min(brutto, 1440)
        pre_shifts[emp_idx].append(
            {
                "date": pre["date"],
                "start_abs": start_abs,
                "end_abs": start_abs + brutto,
                "brutto": brutto,
                "netto": brutto - _law_break_minutes(brutto),
                "week_key": _date_to_week_key(pre["date"]),
            }
        )

    return {
        "config": config,
        "employees": employees,
        "requirements": requirements,
        "wishes": wishes,
        "slots": slots,
        "shift_templates": shift_templates,
        "off_dates": off_dates,
        "pre_shifts": pre_shifts,
        "protected_days": protected_days,
        "sunday_set": sunday_set,
        "saturday_set": saturday_set,
        "holiday_set": holiday_set,
        "all_days": all_days,
        "reference": reference,
        "end_dt": end_dt,
        "start_str": start_str,
        "end_str": end_str,
        "night_window": (night_ws, night_we),
        "maximize_staffing": maximize_staffing,
        "max_consecutive_days": int(config.get("maxConsecutiveDays") or 6),
        "min_rest_minutes": max(0, int(float(config.get("minRestTimeHours") or 11) * 60)),
        "max_daily_minutes": int(float(config.get("maxDailyWorkHours") or 10) * 60),
        "min_free_sundays": int(config.get("minFreeSundaysPerYear") if config.get("minFreeSundaysPerYear") is not None else 15),
        "default_weekly_hours": float(config.get("defaultWeeklyHours") or 40.0),
        "max_same_shift_consecutive": int(config.get("maxSameShiftConsecutive") or 0),
        "rest_shift_worker_minutes": (
            int(float(config["restTimeShiftWorkersHours"]) * 60) if config.get("restTimeShiftWorkersHours") else None
        ),
        "night_max_netto": int(float(config.get("nightWorkMaxHours") or 10.0) * 60),
        "law_weekly_minutes": int(float(config.get("maxWeeklyHoursLaw") or 48.0) * 60),
        "num_search_workers": int(config.get("numSearchWorkers") or 8),
        "random_seed": int(config.get("randomSeed") or 0),
    }


def _rest_minutes_for(ctx: dict, employee: dict) -> int:
    """Ruhezeit des Mitarbeiters: JArbSchG 12h > § 21 Schichtarbeit > § 5 default."""
    if employee.get("isMinor"):
        return MINOR_REST_MINUTES
    if employee.get("isShiftWorker") and ctx["rest_shift_worker_minutes"]:
        return ctx["rest_shift_worker_minutes"]
    return ctx["min_rest_minutes"]


def _is_valid_assignment(ctx: dict, employee: dict, slot: dict, relaxed: frozenset) -> bool:
    """B1: Nur gültige (Mitarbeiter, Slot)-Paare sind zuweisbar; ungültige Paare
    werden hart verboten statt nur nicht belohnt."""
    date = slot["date"]
    if (str(employee.get("id")), date) in ctx["off_dates"] and "off_wishes" not in relaxed:
        return False
    if date in (employee.get("forbiddenDates") or []):
        return False

    protection_until = employee.get("protectionUntil")
    if (
        protection_until
        and "protection" not in relaxed
        and _parse_date(date) <= _parse_date(protection_until)
    ):
        return False

    if "qualifications" not in relaxed:
        required = slot["required_skills"]
        emp_skills = set(employee.get("skills") or [])
        for skill in required:
            if skill not in emp_skills:
                return False
        role_required = _role_from_skills(required)
        if role_required and employee.get("role") != role_required:
            return False

    is_minor = bool(employee.get("isMinor"))
    if is_minor and "minor_rules" not in relaxed:
        if date in ctx["saturday_set"] or date in ctx["sunday_set"] or date in ctx["holiday_set"]:
            return False
        if _overlap_with_daily_window(
            slot["start_abs"], slot["end_abs"], MINOR_NIGHT_START % 1440, MINOR_NIGHT_END % 1440
        ) > 0:
            return False

    is_night_rule_violation = (
        employee.get("isNightWorker")
        and slot["is_night"]
        and "night_rules" not in relaxed
        and slot["netto"] > ctx["night_max_netto"]
    )
    return not is_night_rule_violation


def _compute_validity(ctx: dict, relaxed: frozenset) -> tuple[dict[int, list[int]], dict[int, list[int]]]:
    valid_by_slot: dict[int, list[int]] = {}
    valid_slots_by_emp: dict[int, list[int]] = defaultdict(list)
    for slot in ctx["slots"]:
        valid_emps = [
            emp_idx
            for emp_idx, employee in enumerate(ctx["employees"])
            if _is_valid_assignment(ctx, employee, slot, relaxed)
        ]
        valid_by_slot[slot["index"]] = valid_emps
        for emp_idx in valid_emps:
            valid_slots_by_emp[emp_idx].append(slot["index"])
    return valid_by_slot, valid_slots_by_emp


def _build_cp_model(ctx: dict, relaxed: frozenset, with_objective: bool = True) -> dict:
    """Baut das CP-SAT-Modell. `relaxed` deaktiviert Constraint-Familien (D6-Diagnose)."""
    cp = CpModel()
    slots: list[dict] = ctx["slots"]
    employees: list[dict] = ctx["employees"]
    valid_by_slot, valid_slots_by_emp = _compute_validity(ctx, relaxed)

    assignments: dict[tuple[int, int], object] = {}
    for slot in slots:
        for emp_idx in valid_by_slot[slot["index"]]:
            assignments[(emp_idx, slot["index"])] = cp.new_bool_var(
                f"assign_e{emp_idx}_s{slot['index']}"
            )

    def _vars_for(emp_idx: int, slot_indices: list[int]) -> list:
        return [assignments[(emp_idx, i)] for i in slot_indices if (emp_idx, i) in assignments]

    # Slot-Abdeckung: mandatory == 1 (INFEASIBLE falls keine valid MA, B1), optional <= 1
    for slot in slots:
        slot_vars = [assignments[(e, slot["index"])] for e in valid_by_slot[slot["index"]]]
        if slot["mandatory"]:
            cp.add(LinearExpr.sum(slot_vars) == 1)
        elif slot_vars:
            cp.add(LinearExpr.sum(slot_vars) <= 1)

    # Keine Doppelbesetzung innerhalb derselben (date, shiftId)-Gruppe (B2)
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for slot in slots:
        groups[slot["group"]].append(slot["index"])
    for indices in groups.values():
        if len(indices) > 1:
            for emp_idx in valid_slots_by_emp:
                group_vars = _vars_for(emp_idx, indices)
                if len(group_vars) > 1:
                    cp.add(LinearExpr.sum(group_vars) <= 1)

    # works_on_date je (MA, req-Tag) für Tages-/Sonntags-/Ketten-Constraints
    works: dict[tuple[int, str], object] = {}
    slots_by_date: dict[str, list[int]] = defaultdict(list)
    for slot in slots:
        slots_by_date[slot["date"]].append(slot["index"])
    for emp_idx in valid_slots_by_emp:
        for date, indices in slots_by_date.items():
            day_vars = _vars_for(emp_idx, indices)
            if not day_vars:
                continue
            works_var = cp.new_bool_var(f"works_e{emp_idx}_d{date}")
            works[(emp_idx, date)] = works_var
            cp.add(LinearExpr.sum(day_vars) >= works_var)
            for var in day_vars:
                cp.add(var <= works_var)

    req_days = set(slots_by_date.keys())

    # --- Tagesmaximum § 3/§ 4 (Netto; kumulative Pausen pro Arbeitstag; Teilschichten) ---
    emp_breaks = [int(e.get("breakMinutes") or 0) for e in employees]
    for emp_idx, employee in enumerate(employees):
        if emp_idx not in valid_slots_by_emp:
            continue
        max_daily = ctx["max_daily_minutes"]
        if employee.get("maxDailyHours"):
            max_daily = min(max_daily, int(float(employee["maxDailyHours"]) * 60))
        if employee.get("isMinor") and "minor_rules" not in relaxed:
            max_daily = min(max_daily, MINOR_MAX_DAILY_MINUTES)
        if "daily_max" in relaxed:
            continue
        for date, indices in slots_by_date.items():
            day_vars = _vars_for(emp_idx, indices)
            if not day_vars:
                continue
            pre_brutto = sum(p["brutto"] for p in ctx["pre_shifts"].get(emp_idx, []) if p["date"] == date)
            brutto_terms = [var * slots[i]["brutto"] for var, i in zip(day_vars, indices)]
            brutto_expr = LinearExpr.sum(brutto_terms) + pre_brutto
            brutto_possible = sum(slots[i]["brutto"] for i in indices) + pre_brutto

            b30 = b45 = None
            if brutto_possible > 6 * 60:
                b30 = cp.new_bool_var(f"b30_e{emp_idx}_{date}")
                cp.add(brutto_expr >= 6 * 60 + 1).only_enforce_if(b30)
                cp.add(brutto_expr <= 6 * 60).only_enforce_if(b30.Not())
            if brutto_possible > 9 * 60:
                b45 = cp.new_bool_var(f"b45_e{emp_idx}_{date}")
                cp.add(brutto_expr >= 9 * 60 + 1).only_enforce_if(b45)
                cp.add(brutto_expr <= 9 * 60).only_enforce_if(b45.Not())
            law_expr = 0
            if b30 is not None:
                law_expr += b30 * LAW_BREAK_6H
            if b45 is not None:
                law_expr += b45 * LAW_BREAK_9H_EXTRA
            cp.add(brutto_expr - law_expr <= max_daily)

            rec_terms = [
                var * max(slots[i]["template_min_break"], emp_breaks[emp_idx])
                for var, i in zip(day_vars, indices)
                if max(slots[i]["template_min_break"], emp_breaks[emp_idx]) > 0
            ]
            if rec_terms:
                cp.add(brutto_expr - LinearExpr.sum(rec_terms) <= max_daily)

    # --- Wochenstunden: min(Vertrag, § 3 Gesetz, JArbSchG) inkl. preShifts (C8) ---
    slots_by_week: dict[tuple[int, int], list[int]] = defaultdict(list)
    for slot in slots:
        slots_by_week[_date_to_week_key(slot["date"])].append(slot["index"])
    for emp_idx, employee in enumerate(employees):
        if emp_idx not in valid_slots_by_emp:
            continue
        if "weekly_hours" in relaxed:
            continue
        contract = _emp_contract_hours(employee, ctx["default_weekly_hours"])
        weekly_limit = min(int(contract * 60), ctx["law_weekly_minutes"])
        if employee.get("isMinor") and "minor_rules" not in relaxed:
            weekly_limit = min(weekly_limit, MINOR_MAX_WEEKLY_MINUTES)
        pre_by_week: dict[tuple[int, int], int] = defaultdict(int)
        for pre in ctx["pre_shifts"].get(emp_idx, []):
            pre_by_week[pre["week_key"]] += pre["netto"]
        for week_key in set(list(slots_by_week.keys()) + list(pre_by_week.keys())):
            week_vars = _vars_for(emp_idx, slots_by_week.get(week_key, []))
            pre_netto = pre_by_week.get(week_key, 0)
            if not week_vars and pre_netto == 0:
                continue
            netto_terms = [var * slots[i]["netto"] for var, i in zip(week_vars, slots_by_week.get(week_key, []))]
            cp.add(LinearExpr.sum(netto_terms) + pre_netto <= weekly_limit)

    # --- Ruhezeit § 5/§ 21/§ 16 JArbSchG (absolute Zeiten, B3; Teilschichten, C6) ---
    if "rest_time" not in relaxed:
        for emp_idx, employee in enumerate(employees):
            rest = _rest_minutes_for(ctx, employee)
            ordered = sorted(
                valid_slots_by_emp.get(emp_idx, []),
                key=lambda i: (slots[i]["start_abs"], slots[i]["end_abs"]),
            )
            for a in range(len(ordered)):
                i = ordered[a]
                for b in range(a + 1, len(ordered)):
                    j = ordered[b]
                    if slots[j]["start_abs"] - slots[i]["end_abs"] >= rest:
                        break
                    overlap = slots[i]["end_abs"] > slots[j]["start_abs"]
                    different_workday = slots[i]["date"] != slots[j]["date"]
                    if overlap or (different_workday and slots[j]["start_abs"] - slots[i]["end_abs"] < rest):
                        cp.add(assignments[(emp_idx, i)] + assignments[(emp_idx, j)] <= 1)
            for i in valid_slots_by_emp.get(emp_idx, []):
                slot = slots[i]
                for pre in ctx["pre_shifts"].get(emp_idx, []):
                    a_start, a_end, a_date = slot["start_abs"], slot["end_abs"], slot["date"]
                    b_start, b_end, b_date = pre["start_abs"], pre["end_abs"], pre["date"]
                    if a_start > b_start:
                        a_start, a_end, a_date, b_start, b_end, b_date = b_start, b_end, b_date, a_start, a_end, a_date
                    if a_date == b_date:
                        conflict = a_end > b_start
                    else:
                        conflict = b_start - a_end < rest
                    if conflict:
                        cp.add(assignments[(emp_idx, i)] == 0)

    # --- Sonn-/Feiertagsschonung § 9/§ 11 (Quote ohne stille Abschwächung, B9) ---
    # Erlaubte Arbeitstage an Sonn-/Feiertagen im Zeitraum:
    #   round_half_up((52 - minFree) * SonntageImZeitraum / 52) - protectedDaysWorkedYTD
    # Ohne YTD-Angabe konservative Pro-rata-Näherung auf das Jahreskontingent.
    protected_days = ctx["protected_days"]
    for emp_idx, employee in enumerate(employees):
        if "protected_days" in relaxed:
            break
        protected_work_vars = [works[(emp_idx, d)] for d in protected_days if (emp_idx, d) in works]
        if not protected_work_vars:
            continue
        min_free = ctx["min_free_sundays"]
        if employee.get("minFreeSundaysPerYear") is not None:
            min_free = max(min_free, int(employee["minFreeSundaysPerYear"]))
        budget = (2 * len(protected_days) * (52 - min_free) + 52) // 104
        allowed = max(0, budget - int(employee.get("protectedDaysWorkedYTD") or 0))
        cp.add(LinearExpr.sum(protected_work_vars) <= allowed)

    # --- Ersatzruhetag § 11 Abs. 3 nach Sonn-/Feiertagsarbeit ---
    if "ersatz_rest" not in relaxed:
        end_date = ctx["end_dt"]
        for date in protected_days:
            if date not in req_days:
                continue
            window = _ersatz_window_days(date, date in ctx["sunday_set"], date in ctx["holiday_set"])
            if window <= 0:
                continue
            day_dt = _parse_date(date)
            for emp_idx in valid_slots_by_emp:
                if (emp_idx, date) not in works:
                    continue
                free_vars = []
                satisfied = False
                for offset in range(1, window + 1):
                    target_dt = day_dt + timedelta(days=offset)
                    if target_dt > end_date:
                        satisfied = True
                        break
                    target_key = target_dt.strftime("%Y-%m-%d")
                    if target_key not in req_days or (emp_idx, target_key) not in works:
                        satisfied = True
                        break
                    free_var = cp.new_bool_var(f"free_e{emp_idx}_d{target_key}")
                    cp.add(free_var + works[(emp_idx, target_key)] == 1)
                    free_vars.append(free_var)
                if satisfied:
                    continue
                ersatz = cp.new_bool_var(f"ersatz_e{emp_idx}_d{date}")
                cp.add_max_equality(ersatz, free_vars)
                cp.add(works[(emp_idx, date)] <= ersatz)

    # --- Max. aufeinanderfolgende Arbeitstage über echte Kalendertage (B10) ---
    if "consecutive_days" not in relaxed and ctx["max_consecutive_days"] > 0:
        for emp_idx, employee in enumerate(employees):
            if emp_idx not in valid_slots_by_emp:
                continue
            limit = ctx["max_consecutive_days"]
            if employee.get("maxConsecutiveDays"):
                limit = min(limit, int(employee["maxConsecutiveDays"]))
            day_keys = {d for (e, d) in works if e == emp_idx}
            day_keys.update(p["date"] for p in ctx["pre_shifts"].get(emp_idx, []))
            sorted_days = sorted(day_keys)
            chains: list[list[str]] = []
            for day in sorted_days:
                if chains and _parse_date(day) - _parse_date(chains[-1][-1]) == timedelta(days=1):
                    chains[-1].append(day)
                else:
                    chains.append([day])
            for chain in chains:
                for start in range(max(1, len(chain) - limit)):
                    window_days = chain[start : start + limit + 1]
                    if len(window_days) <= limit:
                        continue
                    terms = [works.get((emp_idx, d), None) for d in window_days]
                    const_count = sum(1 for t in terms if t is None)
                    var_terms = [t for t in terms if t is not None]
                    cp.add(LinearExpr.sum(var_terms) + const_count <= limit)

    # --- maxSameShiftConsecutive über Kalenderketten (B10-Analog) ---
    if "shift_rotation" not in relaxed and ctx["max_same_shift_consecutive"] > 0:
        limit = ctx["max_same_shift_consecutive"]
        for emp_idx in valid_slots_by_emp:
            for shift_id in ctx["shift_templates"]:
                shift_days = sorted(
                    {slots[i]["date"] for i in valid_slots_by_emp[emp_idx] if slots[i]["shift_id"] == shift_id}
                )
                if len(shift_days) <= limit:
                    continue
                chains: list[list[str]] = []
                for day in shift_days:
                    if chains and _parse_date(day) - _parse_date(chains[-1][-1]) == timedelta(days=1):
                        chains[-1].append(day)
                    else:
                        chains.append([day])
                for chain in chains:
                    for start in range(max(1, len(chain) - limit)):
                        window_days = chain[start : start + limit + 1]
                        if len(window_days) <= limit:
                            continue
                        day_works_vars = []
                        for day in window_days:
                            day_slots = [
                                i
                                for i in valid_slots_by_emp[emp_idx]
                                if slots[i]["date"] == day and slots[i]["shift_id"] == shift_id
                            ]
                            day_vars = _vars_for(emp_idx, day_slots)
                            if not day_vars:
                                continue
                            if len(day_vars) == 1:
                                day_works_vars.append(day_vars[0])
                            else:
                                day_var = cp.new_bool_var(f"shiftwork_e{emp_idx}_{day}_{shift_id}")
                                cp.add_max_equality(day_var, day_vars)
                                day_works_vars.append(day_var)
                        if len(day_works_vars) > limit:
                            cp.add(LinearExpr.sum(day_works_vars) <= limit)

    # --- JArbSchG: max. 5 Werktage pro Woche für Minderjährige ---
    if "minor_rules" not in relaxed:
        for emp_idx, employee in enumerate(employees):
            if not employee.get("isMinor") or emp_idx not in valid_slots_by_emp:
                continue
            week_days: dict[tuple[int, int], list[str]] = defaultdict(list)
            for (e, d) in works:
                if e == emp_idx:
                    week_days[_date_to_week_key(d)].append(d)
            for pre in ctx["pre_shifts"].get(emp_idx, []):
                week_days[pre["week_key"]].append(pre["date"])
            for week_key, days in week_days.items():
                var_terms = [works[(emp_idx, d)] for d in days if (emp_idx, d) in works]
                const_count = sum(1 for d in days if (emp_idx, d) not in works)
                cp.add(LinearExpr.sum(var_terms) + const_count <= MINOR_MAX_WORKDAYS_PER_WEEK)

    # --- Wünsche als weiche Constraints (B4: weight-Fallback auf priority; C2: Gruppen) ---
    wish_vars: list[tuple[object, int, dict, int]] = []
    not_applicable: list[dict] = []
    employee_index_by_id = {str(e.get("id")): i for i, e in enumerate(employees)}
    for wish in ctx["wishes"]:
        wish_type = wish.get("type", "")
        if wish_type in ("OFF", "vacation", "unavailable"):
            continue
        if wish_type not in ("PREFER_SHIFT", "preferred"):
            continue
        emp_idx = employee_index_by_id.get(str(wish.get("employeeId")))
        if emp_idx is None:
            continue
        weight = wish.get("weight")
        if weight is None:
            weight = wish.get("priority") if (wish.get("priority") or 0) > 0 else 1
        weight = max(1, int(weight))
        date = wish.get("date")
        if wish_type == "PREFER_SHIFT":
            shift_id = str(wish.get("shiftId") or wish.get("shiftTemplateId") or "")
            matching = [
                i
                for i in valid_slots_by_emp.get(emp_idx, [])
                if slots[i]["date"] == date and slots[i]["shift_id"] == shift_id
            ]
        else:
            matching = [i for i in valid_slots_by_emp.get(emp_idx, []) if slots[i]["date"] == date]
        if not matching:
            not_applicable.append(wish)
            continue
        matching_vars = [assignments[(emp_idx, i)] for i in matching]
        if len(matching_vars) == 1:
            wish_var = matching_vars[0]
        else:
            wish_var = cp.new_bool_var(f"wish_e{emp_idx}_{date}_{wish_type}")
            cp.add_max_equality(wish_var, matching_vars)
        wish_vars.append((wish_var, weight, wish, emp_idx))

    # --- Fairness (B7: Gruppenzugehörigkeit = Zuweisbarkeit; C4/C5/C6: konsistente Basis) ---
    fairness_penalty_vars: list[object] = []
    fairness_targets: dict[int, int] = {}

    def _add_fairness(group_slots: list[int], group_emps: list[int], tag: str, is_global: bool = False) -> None:
        # Fairness misst die Verteilung der PFLICHT-Arbeit (mandatory slots).
        # Optionale Slots bleiben anreizfrei, damit sie ohne maximizeStaffing leer
        # bleiben und Metrik (fairnessDeviation/targetHours) deckungsgleich mit dem
        # Modell ist (C5/C6).
        mandatory_slots = [i for i in group_slots if slots[i]["mandatory"]]
        min_emps = 1 if is_global else 2
        if len(group_emps) < min_emps or not mandatory_slots:
            return
        total = sum(slots[i]["netto"] for i in mandatory_slots)
        if total <= 0:
            return
        contract_total = sum(
            _emp_contract_hours(employees[e], ctx["default_weekly_hours"]) for e in group_emps
        )
        if contract_total <= 0:
            return
        for emp_idx in group_emps:
            contract = _emp_contract_hours(employees[emp_idx], ctx["default_weekly_hours"])
            target = int((contract / contract_total) * total)
            if target <= 0:
                continue
            if is_global:
                fairness_targets[emp_idx] = target
            actual_terms = [
                assignments[(emp_idx, i)] * slots[i]["netto"]
                for i in mandatory_slots
                if (emp_idx, i) in assignments
            ]
            over = cp.new_int_var(0, total, f"over_{tag}_e{emp_idx}")
            under = cp.new_int_var(0, total, f"under_{tag}_e{emp_idx}")
            cp.add(LinearExpr.sum(actual_terms) - target == over - under)
            fairness_penalty_vars.extend([over, under])

    skill_groups: dict[str, list[int]] = defaultdict(list)
    for slot in slots:
        if slot["skill"] and slot["mandatory"]:
            skill_groups[slot["skill"]].append(slot["index"])
    for skill, group_slots in skill_groups.items():
        group_emps = [e for e in valid_slots_by_emp if any(i in group_slots for i in valid_slots_by_emp[e])]
        _add_fairness(group_slots, group_emps, f"skill_{skill}")
    _add_fairness([s["index"] for s in slots], list(valid_slots_by_emp.keys()), "global", is_global=True)

    # --- Zielfunktion (B8: dokumentierte, proportionale Gewichte) ---
    if with_objective:
        objective_terms = []
        for (emp_idx, slot_idx), var in assignments.items():
            slot = slots[slot_idx]
            if slot["mandatory"]:
                objective_terms.append(var * MANDATORY_BONUS)
            elif ctx["maximize_staffing"] and slot["netto"] > 0:
                objective_terms.append(var * (slot["netto"] * OPTIONAL_BONUS_PER_MIN))
        for wish_var, weight, _wish, _emp in wish_vars:
            objective_terms.append(wish_var * (weight * WISH_BONUS_PER_UNIT))
        for var in fairness_penalty_vars:
            objective_terms.append(var * -FAIRNESS_PENALTY_PER_MIN)
        for emp_idx, employee in enumerate(employees):
            balance = float(employee.get("currentBalanceHours") or 0.0)
            if balance == 0:
                continue
            for slot_idx in valid_slots_by_emp.get(emp_idx, []):
                netto = slots[slot_idx]["netto"]
                if netto > 0:
                    bonus = int(-balance * netto * BALANCE_RECOVERY_PER_MIN)
                    if bonus != 0:
                        objective_terms.append(assignments[(emp_idx, slot_idx)] * bonus)
        if objective_terms:
            cp.maximize(LinearExpr.sum(objective_terms))

    return {
        "cp_model": cp,
        "assignments": assignments,
        "valid_by_slot": valid_by_slot,
        "valid_slots_by_emp": valid_slots_by_emp,
        "works": works,
        "wish_vars": wish_vars,
        "not_applicable_wishes": not_applicable,
        "fairness_targets": fairness_targets,
    }


_FAMILY_LABELS = {
    "qualifications": "Qualifikation/Verfügbarkeit (Skills, Rollen, forbiddenDates)",
    "off_wishes": "OFF-/Urlaubs-/Unavailable-Wünsche",
    "protection": "Mutterschutz (protectionUntil)",
    "rest_time": "Ruhezeit § 5/§ 21/§ 16 JArbSchG",
    "daily_max": "Tagesmaximum § 3 ArbZG",
    "weekly_hours": "Wochenstunden (Vertrag/§ 3/JArbSchG)",
    "protected_days": "Sonn-/Feiertagsschonung § 9/§ 11",
    "consecutive_days": "max. aufeinanderfolgende Arbeitstage",
    "shift_rotation": "Schicht-Rotation (maxSameShiftConsecutive)",
    "night_rules": "Nachtarbeit § 6 ArbZG",
    "minor_rules": "JArbSchG-Regeln für Minderjährige",
    "ersatz_rest": "Ersatzruhetag § 11 Abs. 3",
}


def _solve_cp(cp_model: CpModel, timeout: float, num_workers: int, seed: int) -> tuple[CpSolver, int]:
    solver = CpSolver()
    solver.parameters.max_time_in_seconds = max(0.01, float(timeout))
    solver.parameters.num_workers = max(1, int(num_workers))
    solver.parameters.random_seed = int(seed)
    solver.parameters.log_search_progress = False
    status = solver.Solve(cp_model)
    return solver, status


def _status_name(solver: CpSolver, status: int) -> str:
    return solver.status_name(status)


def _diagnose_infeasible(ctx: dict, artifacts: dict, timeout_budget: float) -> list[str]:
    """D6: statische Analyse + gezielte Re-Solves mit entspannten Constraint-Familien."""
    reasons: list[str] = []
    slots = ctx["slots"]
    valid_by_slot = artifacts["valid_by_slot"]

    for slot in slots:
        if slot["mandatory"] and not valid_by_slot[slot["index"]]:
            skills = ", ".join(slot["required_skills"]) or "-"
            reasons.append(
                f"SKILL_COVERAGE: Requirement {slot['date']}/{slot['shift_id']} "
                f"(Skills: {skills}) kann von keinem Mitarbeiter gedeckt werden"
            )
    if reasons:
        return reasons

    per_family_budget = max(1.0, min(5.0, timeout_budget / 4.0))
    overall_deadline = timeout_budget
    for family in RELAX_FAMILIES:
        if len(reasons) >= 3 or overall_deadline <= 0:
            break
        relaxed_artifacts = _build_cp_model(ctx, frozenset({family}), with_objective=False)
        solver, status = _solve_cp(
            relaxed_artifacts["cp_model"], per_family_budget, ctx["num_search_workers"], ctx["random_seed"]
        )
        overall_deadline -= per_family_budget
        if _status_name(solver, status) in ("OPTIMAL", "FEASIBLE"):
            reasons.append(
                f"INFEASIBLE vermutlich verursacht durch: {_FAMILY_LABELS.get(family, family)} "
                f"(ohne diese Constraint-Familie ist das Modell zulässig)"
            )
    return reasons


def _empty_result(ctx: dict, status: str, info: str, solve_time: float, is_optimal: bool) -> dict:
    employees = ctx["employees"]
    preferred_total = 0
    for wish in ctx["wishes"]:
        if wish.get("type", "") in ("PREFER_SHIFT", "preferred") and wish.get("employeeId") in {
            str(e.get("id")) for e in employees
        }:
            preferred_total += 1
    wish_rate = 100.0 if preferred_total == 0 else 0.0
    return {
        "metadata": {
            "status": status,
            "solveTimeSeconds": round(solve_time, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "solution": {
            "assignments": [],
            "unassignedRequirements": [],
        },
        "metrics": {
            "wishFulfillmentRate": wish_rate,
            "totalObjectiveScore": 0,
            "employeeUtilization": {str(e.get("id")): 0.0 for e in employees},
            "employeeFairness": {
                str(e.get("id")): {
                    "currentBalanceHours": round(float(e.get("currentBalanceHours") or 0.0), 2),
                    "scheduledHours": 0.0,
                    "targetHours": 0.0,
                    "projectedBalance": round(float(e.get("currentBalanceHours") or 0.0), 2),
                    "fairnessDeviation": 0.0,
                }
                for e in employees
            },
            "violations": [],
        },
        "diagnostics": {
            "isOptimal": is_optimal,
            "info": info,
            "infeasibilityReasons": [],
        },
    }


def solve_model(model: dict, timeout_seconds: float = 300) -> dict:
    """Löst das Modell mit CP-SAT unter Beachtung des Arbeitsrecht-Regelwerks."""
    start_time = datetime.now(timezone.utc)
    ctx = _prepare(model)
    slots: list[dict] = ctx["slots"]

    if not slots:
        solve_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        return _empty_result(ctx, "SUCCESS", "Keine Anforderungen zu planen.", solve_time, True)

    artifacts = _build_cp_model(ctx, frozenset())
    solver, status = _solve_cp(artifacts["cp_model"], timeout_seconds, ctx["num_search_workers"], ctx["random_seed"])
    solve_time = (datetime.now(timezone.utc) - start_time).total_seconds()
    status_name = _status_name(solver, status)

    if status_name == "MODEL_INVALID":
        raise ValueError(f"CP-SAT Modell ungültig: {solver.ResponseStats()}")

    if status_name not in ("OPTIMAL", "FEASIBLE"):
        if status_name == "INFEASIBLE":
            reasons = _diagnose_infeasible(ctx, artifacts, max(2.0, timeout_seconds / 4.0))
            info = "Keine Lösung gefunden." if not reasons else "Keine Lösung gefunden (siehe Diagnose)."
            return _empty_result(ctx, "INFEASIBLE", info, solve_time, False) | {
                "diagnostics": {"isOptimal": False, "info": info, "infeasibilityReasons": reasons}
            }
        return _empty_result(ctx, "TIMEOUT", "Timeout erreicht, keine zulässige Lösung gefunden.", solve_time, False)

    assignments_solution: list[dict] = []
    assigned_by_orig: dict[int, int] = defaultdict(int)
    employees = ctx["employees"]
    for slot in slots:
        for emp_idx in artifacts["valid_by_slot"][slot["index"]]:
            var = artifacts["assignments"].get((emp_idx, slot["index"]))
            if var is not None and solver.Value(var) == 1:
                employee = employees[emp_idx]
                brutto = slot["brutto"]
                recommended = _recommended_break_minutes(
                    brutto, slot["template_min_break"], int(employee.get("breakMinutes") or 0)
                )
                assignments_solution.append(
                    {
                        "employeeId": employee["id"],
                        "date": slot["date"],
                        "shiftId": slot["shift_id"],
                        "startTime": slot["start_str"],
                        "endTime": slot["end_str"],
                        "name": slot["template"].get("name", ""),
                        "breakMinutes": recommended,
                        "isNightShift": slot["is_night"],
                    }
                )
                assigned_by_orig[slot["orig_index"]] += 1

    # unassignedRequirements originalgetreu (D7)
    unassigned_requirements: list[dict] = []
    violations: list[dict] = []
    orig_counts: dict[int, int] = defaultdict(int)
    orig_total_slots: dict[int, int] = defaultdict(int)
    for slot in slots:
        if slot["mandatory"]:
            orig_counts[slot["orig_index"]] += 1
        orig_total_slots[slot["orig_index"]] += 1
    for orig_index, req in enumerate(ctx["requirements"]):
        expected = orig_total_slots[orig_index]
        assigned = assigned_by_orig.get(orig_index, 0)
        missing = expected - assigned
        if missing <= 0:
            continue
        mandatory_missing = max(0, orig_counts[orig_index] - min(assigned, orig_counts[orig_index]))
        unassigned_requirements.append(
            {
                "date": req.get("date"),
                "shiftId": req.get("shiftId") or req.get("shiftTemplateId"),
                "missingCount": missing,
            }
        )
        violations.append(
            {
                "type": "UNASSIGNED_REQUIREMENT",
                "severity": "HARD" if mandatory_missing > 0 else "SOFT",
                "message": (
                    f"Requirement on {req.get('date')} with shift "
                    f"{req.get('shiftId') or req.get('shiftTemplateId')}: "
                    f"{missing} Slot(s) unbesetzt"
                ),
                "details": {"missingCount": missing, "mandatoryMissing": mandatory_missing},
            }
        )

    # Wunscherfüllung (B14: konsistente Zählung über alle PREFER-Wünsche)
    fulfilled_wishes = 0
    total_wishes = 0
    for wish_var, _weight, wish, _emp in artifacts["wish_vars"]:
        total_wishes += 1
        if solver.Value(wish_var) == 1:
            fulfilled_wishes += 1
        else:
            violations.append(
                {
                    "type": "WISH_NOT_FULFILLED",
                    "severity": "SOFT",
                    "message": (
                        f"Wish for employee {wish.get('employeeId')} on {wish.get('date')} "
                        f"(shift {wish.get('shiftId')}) not fulfilled"
                    ),
                    "details": wish,
                }
            )
    not_applicable_ids = {id(w) for w in artifacts["not_applicable_wishes"]}
    for wish in ctx["wishes"]:
        if wish.get("type", "") not in ("PREFER_SHIFT", "preferred"):
            continue
        if id(wish) in not_applicable_ids:
            total_wishes += 1
            violations.append(
                {
                    "type": "WISH_NOT_APPLICABLE",
                    "severity": "SOFT",
                    "message": (
                        f"Wish for employee {wish.get('employeeId')} on {wish.get('date')} "
                        f"hat kein passendes Requirement und ist nicht erfüllbar"
                    ),
                    "details": wish,
                }
            )
    wish_rate = 100.0 if total_wishes == 0 else round((fulfilled_wishes / total_wishes) * 100, 1)

    # § 6 Abs. 1: Eignungsuntersuchung für Nachtarbeitnehmer (SOFT)
    start_dt = ctx["reference"]
    assigned_emps_with_night = {
        a["employeeId"] for a in assignments_solution if a["isNightShift"]
    }
    for employee in employees:
        if not employee.get("isNightWorker") or str(employee.get("id")) not in assigned_emps_with_night:
            continue
        exam_date = employee.get("nightWorkerExamDate")
        outdated = True
        if exam_date:
            try:
                exam_dt = _parse_date(exam_date)
                outdated = (start_dt - exam_dt).days > EXAM_VALIDITY_DAYS
            except ValueError:
                outdated = True
        if outdated:
            violations.append(
                {
                    "type": "NIGHT_WORKER_EXAM",
                    "severity": "SOFT",
                    "message": (
                        f"Nachtarbeitnehmer {employee.get('id')} hat keine gültige "
                        f"arbeitsmedizinische Eignungsuntersuchung (ArbZG § 6 Abs. 1)"
                    ),
                    "details": {"employeeId": employee.get("id"), "nightWorkerExamDate": exam_date},
                }
            )

    employee_utilization: dict[str, float] = {str(e.get("id")): 0.0 for e in employees}
    utilization_by_idx: dict[int, float] = defaultdict(float)
    for slot in slots:
        for emp_idx in artifacts["valid_by_slot"][slot["index"]]:
            var = artifacts["assignments"].get((emp_idx, slot["index"]))
            if var is not None and solver.Value(var) == 1:
                utilization_by_idx[emp_idx] += slot["netto"] / 60.0
    for emp_idx, employee in enumerate(employees):
        employee_utilization[str(employee.get("id"))] = round(utilization_by_idx.get(emp_idx, 0.0), 2)

    employee_fairness: dict[str, dict] = {}
    for emp_idx, employee in enumerate(employees):
        emp_id = str(employee.get("id"))
        balance = float(employee.get("currentBalanceHours") or 0.0)
        scheduled = employee_utilization.get(emp_id, 0.0)
        target_hours = artifacts["fairness_targets"].get(emp_idx, 0) / 60.0
        projected = balance + (scheduled - target_hours)
        deviation = abs(scheduled - target_hours + balance)
        employee_fairness[emp_id] = {
            "currentBalanceHours": round(balance, 2),
            "scheduledHours": round(scheduled, 2),
            "targetHours": round(target_hours, 2),
            "projectedBalance": round(projected, 2),
            "fairnessDeviation": round(deviation, 2),
        }

    if status_name == "OPTIMAL":
        solver_status = "SUCCESS"
        is_optimal = True
        info = "Optimale Lösung gefunden."
    else:
        solver_status = "FEASIBLE"
        is_optimal = False
        info = "Zulässige Lösung gefunden, aber nicht nachweislich optimal."

    try:
        objective_value = round(solver.ObjectiveValue())
    except Exception:  # noqa: BLE001 -ObjectiveValue ohne maximize ist 0
        objective_value = 0

    return {
        "metadata": {
            "status": solver_status,
            "solveTimeSeconds": round(solve_time, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "solution": {
            "assignments": assignments_solution,
            "unassignedRequirements": unassigned_requirements,
        },
        "metrics": {
            "wishFulfillmentRate": wish_rate,
            "totalObjectiveScore": objective_value,
            "employeeUtilization": employee_utilization,
            "employeeFairness": employee_fairness,
            "violations": violations,
        },
        "diagnostics": {
            "isOptimal": is_optimal,
            "info": info,
            "infeasibilityReasons": [],
        },
    }
