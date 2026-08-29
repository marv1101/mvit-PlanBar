import logging
import math
from collections import defaultdict
from datetime import datetime, timezone

from ortools.sat.python.cp_model import CpModel, CpSolver, CpSolverStatus, LinearExpr

from .schema import JobPayload


def build_model(payload: dict | JobPayload) -> dict:
    """
    Übersetze das Eingabe-Payload in ein vorläufiges Modell.
    Akzeptiert sowohl dict als auch JobPayload (Pydantic).
    """
    if isinstance(payload, JobPayload):
        # Wenn Pydantic-Modell übergeben wird, use model_dump()
        payload_dict = payload.model_dump()
    else:
        payload_dict = payload

    model = {
        "metadata": payload_dict.get("metadata", {}),
        "config": payload_dict.get("config", {}),
        "shiftTemplates": {item["id"]: item for item in (payload_dict.get("shiftTemplates") or [])},
        "requirements": payload_dict.get("requirements", []),
        "employees": payload_dict.get("employees", []),
        "wishes": payload_dict.get("wishes") or [],
    }
    return model


def _time_to_minutes(time_str: str) -> int:
    """Konvertiere HH:MM String zu Minuten seit Mitternacht."""
    hours, minutes = map(int, time_str.split(":"))
    return hours * 60 + minutes


def _date_to_days(start_date_str: str, target_date_str: str) -> int:
    """Berechne Anzahl Tage zwischen zwei Daten (YYYY-MM-DD)."""
    start = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    target = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (target - start).days


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _date_to_week_key(date_str: str) -> tuple[int, int]:
    dt = _parse_date(date_str)
    year, week, _ = dt.isocalendar()
    return year, week


def _is_sunday(date_str: str) -> bool:
    return _parse_date(date_str).weekday() == 6


def _shift_duration_minutes(shift: dict) -> int:
    start = _time_to_minutes(shift.get("startTime", "00:00"))
    end = _time_to_minutes(shift.get("endTime", "00:00"))
    duration = end - start
    if duration <= 0:
        duration += 24 * 60
    return duration


def _required_break_minutes(shift: dict, employee: dict) -> int:
    duration = _shift_duration_minutes(shift)
    break_from_shift = shift.get("minBreakMinutes", 0) or 0
    break_from_employee = employee.get("breakMinutes", 0) or 0
    required_break = 0
    if duration >= 9 * 60:
        required_break = 45
    elif duration >= 6 * 60:
        required_break = 30
    return max(required_break, break_from_shift, break_from_employee)


def _effective_shift_minutes(shift: dict, employee: dict) -> int:
    duration = _shift_duration_minutes(shift)
    break_minutes = _required_break_minutes(shift, employee)
    return max(0, duration - break_minutes)


def solve_model(model: dict, timeout_seconds: int) -> dict:
    """Löse das Modell mit Google OR-Tools unter Berücksichtigung aller Constraints."""
    start_time = datetime.now(timezone.utc)

    cp_model = CpModel()

    # Extrahiere Daten
    model.get("metadata", {})
    config = model.get("config", {})
    shift_templates = model["shiftTemplates"]
    employees = model.get("employees", [])
    requirements = model.get("requirements", [])
    wishes = model.get("wishes") or []

    start_date = config.get("startDate", "2026-01-01")
    end_date = config.get("endDate", "2026-01-31")

    max_consecutive_days = config.get("maxConsecutiveDays", 6)
    min_rest_hours = config.get("minRestTimeHours", 11)
    max_daily_hours = config.get("maxDailyWorkHours", 10)
    min_free_sundays_per_year = config.get("minFreeSundaysPerYear", 15)
    default_weekly_hours = config.get("defaultWeeklyHours", 40.0)
    max_same_shift_consecutive = config.get("maxSameShiftConsecutive", 0)
    maximize_staffing = config.get("maximizeStaffing", False)
    holiday_dates_raw = config.get("holidayDates") or []

    # Expand requirements by count
    expanded_requirements = []
    for req in requirements:
        count = req.get("count", 1)
        max_count = req.get("maxCount")

        # Auto-expand for maximizeStaffing without explicit maxCount
        if maximize_staffing and not max_count:
            # Count qualified employees for this requirement
            needed_skills = req.get("neededSkills") or {}
            if not needed_skills:
                skills_list = req.get("skills") or []
                needed_skills = {s: 1 for s in skills_list}
            qualified = 0
            for emp in employees:
                emp_skills = set(emp.get("skills") or [])
                has_required = all(s in emp_skills for s in needed_skills)
                if has_required:
                    # Check role constraint
                    role_required = None
                    for skill in needed_skills:
                        if skill.startswith("ROLE_"):
                            role_required = skill.replace("ROLE_", "")
                            break
                    if role_required and emp.get("role") != role_required:
                        continue
                    qualified += 1
            if qualified > count:
                max_count = qualified

        total_slots = max_count if max_count and max_count > count else count
        for i in range(total_slots):
            expanded = dict(req)
            expanded["count"] = 1
            expanded["mandatory"] = (i < count)
            expanded_requirements.append(expanded)
    requirements = expanded_requirements

    if not requirements:
        solve_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Wishes can still exist even if there are no requirements to assign.
        # OFF/vacation/unavailable wishes are fulfilled automatically when there
        # is no work; preferred/PREFER_SHIFT wishes cannot be fulfilled.
        fulfilled_wishes = 0
        total_wishes = 0
        for wish in wishes:
            wish_type = wish.get("type", "")
            if wish_type in ("OFF", "vacation", "unavailable"):
                fulfilled_wishes += 1
                total_wishes += 1
            elif wish_type in ("PREFER_SHIFT", "preferred"):
                total_wishes += 1
        wish_rate = 100.0 if total_wishes == 0 else round((fulfilled_wishes / total_wishes) * 100, 1)

        return {
            "metadata": {
                "status": "SUCCESS",
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
                "employeeUtilization": {emp["id"]: 0.0 for emp in employees},
                "employeeFairness": {
                    emp["id"]: {
                        "currentBalanceHours": round(float(emp.get("currentBalanceHours", 0.0) or 0.0), 2),
                        "scheduledHours": 0.0,
                        "targetHours": 0.0,
                        "projectedBalance": round(float(emp.get("currentBalanceHours", 0.0) or 0.0), 2),
                        "fairnessDeviation": 0.0,
                    }
                    for emp in employees
                },
                "violations": [],
            },
            "diagnostics": {
                "isOptimal": True,
                "info": "Keine Anforderungen zu planen.",
            },
        }

    date_requirements: dict[str, list[int]] = defaultdict(list)
    week_requirements: dict[tuple[int, int], list[int]] = defaultdict(list)
    for req_idx, requirement in enumerate(requirements):
        req_date = requirement.get("date")
        if req_date:
            date_requirements[req_date].append(req_idx)
            week_requirements[_date_to_week_key(req_date)].append(req_idx)

    unique_dates = sorted(date_requirements.keys())
    if unique_dates:
        (_parse_date(unique_dates[-1]) - _parse_date(unique_dates[0])).days + 1

    # Erstelle Decision Variables
    # assignment[emp_id, req_idx] = 1 wenn Mitarbeiter emp_id zu Requirement req_idx zugewiesen
    assignments = {}
    for emp_idx, employee in enumerate(employees):
        for req_idx, requirement in enumerate(requirements):
            assignments[(emp_idx, req_idx)] = cp_model.new_bool_var(f"assign_emp{emp_idx}_req{req_idx}")

    # Constraint 1: Skill- und Verfügbarkeitsprüfung
    for req_idx, requirement in enumerate(requirements):
        needed_skills = requirement.get("neededSkills") or {}
        if not needed_skills:
            skills_list = requirement.get("skills") or []
            needed_skills = {s: 1 for s in skills_list}
        valid_employees = []

        for emp_idx, employee in enumerate(employees):
            date = requirement.get("date")
            # Prüfe ob Mitarbeiter verfügbar ist
            if date in (employee.get("forbiddenDates") or []):
                continue

            # Prüfe Skills
            employee_skills = set(employee.get("skills") or [])
            has_required_skills = all(skill in employee_skills for skill in needed_skills)
            if not has_required_skills:
                continue

            # Rollentrennung: Wenn ein Skill mit "ROLE_" beginnt, wird er als Rollenanforderung gewertet.
            role_required = None
            for skill in needed_skills:
                if skill.startswith("ROLE_"):
                    role_required = skill.replace("ROLE_", "")
                    break

            if role_required and employee.get("role") != role_required:
                continue

            valid_employees.append(emp_idx)

        requirement_assignments = [assignments[(ei, req_idx)] for ei in valid_employees]
        if requirement_assignments:
            if requirement.get("mandatory", True):
                cp_model.add(LinearExpr.sum(requirement_assignments) == 1)
            else:
                cp_model.add(LinearExpr.sum(requirement_assignments) <= 1)

    # Constraint 1b: Verhindere Doppelbesetzung bei count > 1
    # Gleicher Mitarbeiter darf nicht zwei expandierte Slots derselben Schicht am selben Tag besetzen
    same_shift_day_groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for req_idx, requirement in enumerate(requirements):
        key = (requirement.get("date", ""), requirement.get("shiftId", ""))
        same_shift_day_groups[key].append(req_idx)
    for req_indices in same_shift_day_groups.values():
        if len(req_indices) > 1:
            for emp_idx in range(len(employees)):
                cp_model.add(LinearExpr.sum([assignments[(emp_idx, ri)] for ri in req_indices]) <= 1)

    # Constraint 2: Stunden-Fairness als Soft Constraint
    # a) Rollen-Gruppen-basierte Fairness (wenn Skills definiert)
    # b) Globale Fairness mit Balance-Adjustment (immer)
    fairness_deviation_vars = []

    if start_date and end_date:
        weeks_in_period = max(1, math.ceil((_parse_date(end_date) - _parse_date(start_date)).days / 7.0))
    else:
        weeks_in_period = 1

    # --- a) Per-Skill-Group Fairness (nur wenn requirements Skills definieren) ---
    all_needed_skills: set[str] = set()
    for requirement in requirements:
        needed = requirement.get("neededSkills") or {}
        all_needed_skills.update(needed.keys())
        skills_list = requirement.get("skills") or []
        all_needed_skills.update(skills_list)

    for skill in sorted(all_needed_skills):
        group_req_indices = [
            i
            for i, req in enumerate(requirements)
            if (skill in (req.get("neededSkills") or {}) or skill in (req.get("skills") or []))
            and req.get("mandatory", True)
        ]
        if not group_req_indices:
            continue

        group_emp_indices = []
        for i, emp in enumerate(employees):
            emp_skills = set(emp.get("skills") or [])
            if skill in emp_skills or skill.startswith("ROLE_") and emp.get("role") == skill.replace("ROLE_", ""):
                group_emp_indices.append(i)
        if len(group_emp_indices) < 2:
            continue

        total_group_minutes = 0
        for req_idx in group_req_indices:
            requirement = requirements[req_idx]
            if not requirement.get("mandatory", True):
                continue
            shift = shift_templates.get(requirement.get("shiftId"), {})
            total_group_minutes += _effective_shift_minutes(shift, {})

        group_contract_minutes = 0.0
        for emp_idx in group_emp_indices:
            emp = employees[emp_idx]
            contract_hours = float(
                emp.get("contractHours") or (emp.get("contract") or {}).get("weeklyHours", default_weekly_hours)
            )
            group_contract_minutes += contract_hours * weeks_in_period * 60

        if group_contract_minutes <= 0:
            continue

        max_possible = 24 * 60 * len(group_req_indices)

        for emp_idx in group_emp_indices:
            emp = employees[emp_idx]
            contract_hours = float(
                emp.get("contractHours") or (emp.get("contract") or {}).get("weeklyHours", default_weekly_hours)
            )
            emp_contract_minutes = contract_hours * weeks_in_period * 60
            anteil = emp_contract_minutes / group_contract_minutes
            target_minutes = int(anteil * total_group_minutes)

            current_balance = float(emp.get("currentBalanceHours", 0.0) or 0.0)
            adjusted_target = max(1, target_minutes - int(current_balance * 60))

            actual_minutes_expr = LinearExpr.sum(
                [
                    assignments[(emp_idx, req_idx)]
                    * _effective_shift_minutes(
                        shift_templates.get(requirements[req_idx].get("shiftId"), {}),
                        emp,
                    )
                    for req_idx in group_req_indices
                ]
            )

            over = cp_model.new_int_var(0, max_possible, f"over_s{skill}_e{emp_idx}")
            under = cp_model.new_int_var(0, max_possible, f"under_s{skill}_e{emp_idx}")
            cp_model.add(actual_minutes_expr - adjusted_target == over - under)

            fairness_deviation_vars.append(over)
            fairness_deviation_vars.append(under)

    # --- b) Globale Fairness mit Balance-Adjustment (immer aktiv) ---
    mandatory_indices = [i for i, r in enumerate(requirements) if r.get("mandatory", True)]
    total_all_minutes = sum(
        _effective_shift_minutes(shift_templates.get(requirements[i].get("shiftId"), {}), {})
        for i in mandatory_indices
    )

    total_contract_minutes = sum(
        float(emp.get("contractHours") or (emp.get("contract") or {}).get("weeklyHours", default_weekly_hours))
        * weeks_in_period
        * 60
        for emp in employees
    )

    if total_contract_minutes > 0 and len(employees) > 1:
        max_possible_global = 24 * 60 * len(requirements)

        for emp_idx, employee in enumerate(employees):
            contract_hours = float(
                employee.get("contractHours")
                or (employee.get("contract") or {}).get("weeklyHours", default_weekly_hours)
            )
            emp_contract_minutes = contract_hours * weeks_in_period * 60
            anteil = emp_contract_minutes / total_contract_minutes
            target_minutes = max(1, int(anteil * total_all_minutes))

            current_balance = float(employee.get("currentBalanceHours", 0.0) or 0.0)
            adjusted_target = max(1, target_minutes - int(current_balance * 60))

            actual_minutes_expr = LinearExpr.sum(
                [
                    assignments[(emp_idx, req_idx)]
                    * _effective_shift_minutes(
                        shift_templates.get(requirements[req_idx].get("shiftId"), {}),
                        employee,
                    )
                    for req_idx in mandatory_indices
                ]
            )

            over = cp_model.new_int_var(0, max_possible_global, f"over_global_e{emp_idx}")
            under = cp_model.new_int_var(0, max_possible_global, f"under_global_e{emp_idx}")
            cp_model.add(actual_minutes_expr - adjusted_target == over - under)

            fairness_deviation_vars.append(over)
            fairness_deviation_vars.append(under)

    num_workers = len(employees)

    # Constraint 3: Mindest-Ruhezeit zwischen Schichten (Hard Constraint)
    # Zwischen zwei Schichten eines Mitarbeiters müssen mindestens min_rest_hours liegen
    if min_rest_hours > 0 and len(requirements) > 1:
        min_rest_minutes = min_rest_hours * 60

        for emp_idx in range(num_workers):
            # Für jedes Paar von Requirements prüfen, ob die Ruhezeit verletzt würde
            for req_i in range(len(requirements)):
                for req_j in range(req_i + 1, len(requirements)):
                    req_i_data = requirements[req_i]
                    req_j_data = requirements[req_j]

                    date_i = req_i_data.get("date")
                    date_j = req_j_data.get("date")
                    shift_id_i = req_i_data.get("shiftId")
                    shift_id_j = req_j_data.get("shiftId")

                    shift_i = shift_templates.get(shift_id_i, {})
                    shift_j = shift_templates.get(shift_id_j, {})

                    # Berechne Start- und Endzeiten in Minuten für beide Schichten
                    start_i = _time_to_minutes(shift_i.get("startTime", "00:00"))
                    end_i = _time_to_minutes(shift_i.get("endTime", "00:00"))
                    start_j = _time_to_minutes(shift_j.get("startTime", "00:00"))
                    end_j = _time_to_minutes(shift_j.get("endTime", "00:00"))

                    days_diff = (_parse_date(date_j) - _parse_date(date_i)).days

                    rest_ij = days_diff * 24 * 60 + (start_j - end_i)
                    rest_ji = -days_diff * 24 * 60 + (start_i - end_j)

                    if rest_ij < min_rest_minutes and rest_ji < min_rest_minutes:
                        cp_model.add(assignments[(emp_idx, req_i)] + assignments[(emp_idx, req_j)] <= 1)

    # Neue Constraints: Tagesarbeitszeit, Sonntagsruhe, max. aufeinanderfolgende Tage und Wochenstunden
    works_on_date = {}
    daily_max_minutes = int(max_daily_hours * 60)
    sunday_dates = [date for date in unique_dates if _is_sunday(date)]
    # ArbZG §9: public holidays are treated like Sundays for work limit purposes
    holiday_dates = [d for d in holiday_dates_raw if d in unique_dates]
    protected_dates = sorted(set(sunday_dates + holiday_dates))
    if len(protected_dates) > 0:
        required_free_days = round(min_free_sundays_per_year * (len(protected_dates) / 52.0))
        allowed_protected_workdays = max(0, len(protected_dates) - min(required_free_days, len(protected_dates) - 1))
    else:
        required_free_days = 0
        allowed_protected_workdays = 0

    for emp_idx, employee in enumerate(employees):
        for date, req_indices in date_requirements.items():
            works_on_date[(emp_idx, date)] = cp_model.new_bool_var(f"works_emp{emp_idx}_{date}")
            cp_model.add(
                sum(assignments[(emp_idx, req_idx)] for req_idx in req_indices) >= works_on_date[(emp_idx, date)]
            )
            for req_idx in req_indices:
                cp_model.add(assignments[(emp_idx, req_idx)] <= works_on_date[(emp_idx, date)])

            effective_day_minutes = []
            for req_idx in req_indices:
                requirement = requirements[req_idx]
                shift = shift_templates.get(requirement.get("shiftId"), {})
                effective_day_minutes.append(
                    assignments[(emp_idx, req_idx)] * _effective_shift_minutes(shift, employee)
                )

            if effective_day_minutes:
                cp_model.add(LinearExpr.sum(effective_day_minutes) <= daily_max_minutes)

        if protected_dates:
            protected_work_flags = [works_on_date[(emp_idx, date)] for date in protected_dates]
            cp_model.add(LinearExpr.sum(protected_work_flags) <= allowed_protected_workdays)

        # Maximal aufeinanderfolgende Arbeitstage
        if max_consecutive_days > 0 and len(unique_dates) > max_consecutive_days:
            for index in range(len(unique_dates) - max_consecutive_days):
                window = unique_dates[index : index + max_consecutive_days + 1]
                cp_model.add(
                    LinearExpr.sum([works_on_date[(emp_idx, date)] for date in window]) <= max_consecutive_days
                )

        # Wochenarbeitszeit basierend auf Vertrag
        weekly_hours = float(
            employee.get("contractHours") or (employee.get("contract") or {}).get("weeklyHours", default_weekly_hours)
        )
        weekly_limit_minutes = int(weekly_hours * 60)
        for req_indices in week_requirements.values():
            weekly_minutes = []
            for req_idx in req_indices:
                requirement = requirements[req_idx]
                shift = shift_templates.get(requirement.get("shiftId"), {})
                weekly_minutes.append(assignments[(emp_idx, req_idx)] * _effective_shift_minutes(shift, employee))
            if weekly_minutes:
                cp_model.add(LinearExpr.sum(weekly_minutes) <= weekly_limit_minutes)

        if max_same_shift_consecutive > 0:
            for shift_id in shift_templates:
                shift_dates = []
                for d in unique_dates:
                    for r_idx in date_requirements[d]:
                        if requirements[r_idx].get("shiftId") == shift_id:
                            shift_dates.append(d)
                            break
                shift_dates.sort()

                if len(shift_dates) > max_same_shift_consecutive:
                    for i in range(len(shift_dates) - max_same_shift_consecutive):
                        window_dates = shift_dates[i : i + max_same_shift_consecutive + 1]
                        window_assignments = []
                        for d in window_dates:
                            day_reqs = [
                                assignments[(emp_idx, r_idx)]
                                for r_idx in date_requirements[d]
                                if requirements[r_idx].get("shiftId") == shift_id
                            ]
                            if day_reqs:
                                day_works_shift = cp_model.new_bool_var(f"emp{emp_idx}_date{d}_shift{shift_id}")
                                cp_model.add(LinearExpr.sum(day_reqs) >= day_works_shift)
                                for var in day_reqs:
                                    cp_model.add(var <= day_works_shift)
                                window_assignments.append(day_works_shift)

                        if len(window_assignments) > max_same_shift_consecutive:
                            cp_model.add(LinearExpr.sum(window_assignments) <= max_same_shift_consecutive)

    # Constraint 3b: OFF-/Urlaubs-/Nicht-verfügbar-Wünsche als harte Constraints
    # Wenn ein Mitarbeiter einen solchen Wunsch für ein Datum hat, darf er an
    # diesem Tag keiner Schicht zugewiesen werden.
    for wish in wishes:
        wish_type = wish.get("type", "")
        if wish_type not in ("OFF", "vacation", "unavailable"):
            continue
        employee_id = wish.get("employeeId")
        off_date = wish.get("date")

        emp_idx = next(
            (i for i, e in enumerate(employees) if e.get("id") == employee_id),
            None
        )
        if emp_idx is None:
            continue

        # Finde alle Requirements an diesem Datum
        for req_idx, requirement in enumerate(requirements):
            if requirement.get("date") == off_date:
                cp_model.add(assignments[(emp_idx, req_idx)] == 0)

    # Constraint 4: Wünsche als weiche Constraints
    wish_penalty_vars = []
    for wish in wishes:
        wish_type = wish.get("type", "")
        employee_id = wish.get("employeeId")
        weight = wish.get("weight", 1)

        emp_idx = next((i for i, e in enumerate(employees) if e.get("id") == employee_id), None)
        if emp_idx is None:
            continue

        if wish_type == "PREFER_SHIFT":
            date = wish.get("date")
            shift_id = wish.get("shiftId")

            # Finde passende Requirement
            matching_req = next(
                (i for i, r in enumerate(requirements) if r.get("date") == date and r.get("shiftId") == shift_id),
                None,
            )

            if matching_req is not None:
                # Variable ob Wunsch erfüllt ist
                wish_fulfilled = cp_model.new_bool_var(f"wish_fulfill_{emp_idx}_{date}_{shift_id}")
                cp_model.add(wish_fulfilled == assignments[(emp_idx, matching_req)])
                wish_penalty_vars.append((wish_fulfilled, weight))

        elif wish_type == "preferred":
            # Generelle Tagespräferenz (optional ohne shiftId): Mitarbeiter bevorzugt
            # an diesem Tag zu arbeiten, unabhängig von der konkreten Schicht.
            date = wish.get("date")
            day_reqs = [
                assignments[(emp_idx, req_idx)]
                for req_idx, req in enumerate(requirements)
                if req.get("date") == date
            ]

            if day_reqs:
                wish_fulfilled = cp_model.new_bool_var(f"wish_fulfill_preferred_{emp_idx}_{date}")
                cp_model.add_max_equality(wish_fulfilled, day_reqs)
                wish_penalty_vars.append((wish_fulfilled, weight))

    # Zielfunktion: Maximiere mit Prioritäten
    # Priorität 1: Anforderungen erfüllen × 10000
    # Priorität 2: Wünsche erfüllen × 100
    # Priorität 3: Fairness-Abweichungen minimieren × -10
    # Priorität 4: Balance Recovery (MA mit negativem Saldo bevorzugen)
    objective_terms = []

    for (emp_idx, req_idx), value in assignments.items():
        req = requirements[req_idx]
        if req.get("mandatory", True):
            objective_terms.append(value * 10000)
        elif maximize_staffing:
            shift = shift_templates.get(req.get("shiftId"), {})
            minutes = _effective_shift_minutes(shift, {})
            objective_terms.append(value * minutes * 10)

    for wish_var, weight in wish_penalty_vars:
        objective_terms.append(wish_var * weight * 100)

    for var in fairness_deviation_vars:
        objective_terms.append(var * -5000)

    # Balance Recovery: Bonus/Penalty pro Assignment basierend auf Zeitkontostand
    # Proportionale Skalierung mit Schichtdauer, damit längere Schichten stärker
    # zum Ausgleich beitragen. Basis: alter Pauschalbetrag int(-balance * 500)
    # für eine 8h-Schicht (480 min), skaliert auf tatsächliche Minuten.
    balance_recovery_terms = []
    for emp_idx, employee in enumerate(employees):
        balance = float(employee.get("currentBalanceHours", 0.0) or 0.0)
        if balance != 0:
            for req_idx in range(len(requirements)):
                shift = shift_templates.get(requirements[req_idx].get("shiftId"), {})
                minutes = _effective_shift_minutes(shift, employee)
                if minutes > 0:
                    bonus = int(-balance * minutes * 500 / 480)
                else:
                    bonus = 0
                balance_recovery_terms.append(assignments[(emp_idx, req_idx)] * bonus)

    objective_terms.extend(balance_recovery_terms)

    if objective_terms:
        cp_model.maximize(LinearExpr.sum(objective_terms))

    # Solver mit Timeout
    solver = CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.log_search_progress = False

    status = solver.Solve(cp_model)

    solve_time = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Extrahiere Lösung
    assignments_solution = []
    unassigned_requirements = []
    violations = []

    try:
        for req_idx, requirement in enumerate(requirements):
            assigned = False
            for emp_idx, employee in enumerate(employees):
                if solver.Value(assignments[(emp_idx, req_idx)]) == 1:
                    shift_id = requirement.get("shiftId")
                    date = requirement.get("date")
                    shift = shift_templates.get(shift_id, {})

                    assignments_solution.append(
                        {
                            "employeeId": employee["id"],
                            "date": date,
                            "shiftId": shift_id,
                            "startTime": shift.get("startTime", "00:00"),
                            "endTime": shift.get("endTime", "00:00"),
                            "name": shift.get("name", ""),
                        }
                    )
                    assigned = True
                    break

            if not assigned:
                unassigned_requirements.append(requirement)
                violations.append(
                    {
                        "type": "UNASSIGNED_REQUIREMENT",
                        "severity": "HARD",
                        "message": f"Requirement on {requirement.get('date')} with shift {requirement.get('shiftId')} could not be assigned",
                        "details": requirement,
                    }
                )
    except (KeyError, IndexError, AttributeError, RuntimeError) as e:
        assignments_solution = []
        unassigned_requirements = requirements
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not extract solution: {e}")

    # Berechne Metriken
    try:
        fulfilled_wishes = sum(solver.Value(wish_var) for wish_var, _ in wish_penalty_vars)
        total_wishes = len(wish_penalty_vars)
        wish_rate = 100.0 if total_wishes == 0 else round((fulfilled_wishes / total_wishes) * 100, 1)

        # Wünsche als Soft-Constraint-Verletzungen tracken
        for wish in wishes:
            wish_type = wish.get("type", "")
            employee_id = wish.get("employeeId")

            emp_idx = next((i for i, e in enumerate(employees) if e.get("id") == employee_id), None)
            if emp_idx is None:
                continue

            if wish_type == "PREFER_SHIFT":
                date = wish.get("date")
                shift_id = wish.get("shiftId")
                matching_req = next(
                    (i for i, r in enumerate(requirements) if r.get("date") == date and r.get("shiftId") == shift_id),
                    None,
                )
                if matching_req is not None and solver.Value(assignments[(emp_idx, matching_req)]) == 0:
                    violations.append(
                        {
                            "type": "WISH_NOT_FULFILLED",
                            "severity": "SOFT",
                            "message": f"Wish for employee {employee_id} on {date} (shift {shift_id}) not fulfilled",
                            "details": wish,
                        }
                    )

            elif wish_type == "preferred":
                date = wish.get("date")
                day_reqs = [
                    req_idx
                    for req_idx, req in enumerate(requirements)
                    if req.get("date") == date
                ]
                if day_reqs and not any(solver.Value(assignments[(emp_idx, req_idx)]) == 1 for req_idx in day_reqs):
                    violations.append(
                        {
                            "type": "WISH_NOT_FULFILLED",
                            "severity": "SOFT",
                            "message": f"Preferred wish for employee {employee_id} on {date} not fulfilled",
                            "details": wish,
                        }
                    )
    except (KeyError, IndexError, AttributeError, ValueError) as e:
        fulfilled_wishes = 0
        wish_rate = 0.0
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not calculate wish metrics: {e}")

    # Bestimme Status
    if status == CpSolverStatus.OPTIMAL:  # OPTIMAL
        solver_status = "SUCCESS"
        is_optimal = True
        info = "Optimale Lösung gefunden."
    elif status == CpSolverStatus.FEASIBLE:  # FEASIBLE
        solver_status = "FEASIBLE"
        is_optimal = False
        info = "Zulässige Lösung gefunden, aber nicht optimal."
    elif status == CpSolverStatus.UNKNOWN:  # UNKNOWN (timeout or interrupted)
        # Check if we have a feasible solution despite timeout
        if solver.BestObjectiveBound() > -float("inf"):
            solver_status = "TIMEOUT"
            is_optimal = False
            info = "Timeout erreicht, aber zulässige Lösung gefunden."
        else:
            solver_status = "TIMEOUT"
            is_optimal = False
            info = "Timeout erreicht, keine Lösung gefunden."
    elif status == CpSolverStatus.MODEL_INVALID:  # MODEL_INVALID
        solver_status = "MODEL_INVALID"
        is_optimal = False
        info = f"MODEL_INVALID: {solver.ResponseStats()}"
    else:  # INFEASIBLE oder NO_SOLUTION_FOUND
        solver_status = "INFEASIBLE"
        is_optimal = False
        info = "Keine Lösung gefunden."

    # Berechne Employee Utilization
    employee_utilization = {emp["id"]: 0.0 for emp in employees}
    for assignment in assignments_solution:
        emp_id = assignment["employeeId"]
        shift_id = assignment["shiftId"]
        shift = shift_templates.get(shift_id, {})

        emp = next((e for e in employees if e["id"] == emp_id), {})
        effective_hours = _effective_shift_minutes(shift, emp) / 60.0
        employee_utilization[emp_id] = employee_utilization.get(emp_id, 0.0) + effective_hours

    # Berechne Fairness-Metriken pro Employee
    employee_fairness = {}
    all_needed_skills_set = set()
    for requirement in requirements:
        needed = requirement.get("neededSkills") or {}
        all_needed_skills_set.update(needed.keys())

    if start_date and end_date:
        weeks_in_period = max(1, math.ceil((_parse_date(end_date) - _parse_date(start_date)).days / 7.0))
    else:
        weeks_in_period = 1

    # Pro Employee: Sammle scheduledHours und berechne targetMinutes
    for emp in employees:
        emp_id = emp["id"]
        scheduled_hours = employee_utilization.get(emp_id, 0.0)
        current_balance = float(emp.get("currentBalanceHours", 0.0) or 0.0)

        contract_hours = float(
            emp.get("contractHours") or (emp.get("contract") or {}).get("weeklyHours", default_weekly_hours)
        )

        # Berechne target (proportionale Stunden basierend auf Contract)
        total_contract_minutes = sum(
            float(e.get("contractHours") or (e.get("contract") or {}).get("weeklyHours", default_weekly_hours))
            * weeks_in_period
            * 60
            for e in employees
        )
        mandatory_reqs_for_fairness = [r for r in requirements if r.get("mandatory", True)]
        total_requirement_minutes = sum(
            _effective_shift_minutes(shift_templates.get(req.get("shiftId"), {}), {}) for req in mandatory_reqs_for_fairness
        )

        if total_contract_minutes > 0:
            emp_contract_minutes = contract_hours * weeks_in_period * 60
            target_hours = (emp_contract_minutes / total_contract_minutes) * total_requirement_minutes / 60.0
        else:
            target_hours = 0.0

        projected_balance = current_balance + (scheduled_hours - target_hours)

        # Berechne fairnessDeviation (Abweichung der Ist-Stunden vom adjustierten Target)
        # Hier: scheduled_hours - (target_hours - current_balance) = scheduled_hours - target_hours + current_balance
        deviation = abs(scheduled_hours - target_hours + current_balance)

        employee_fairness[emp_id] = {
            "currentBalanceHours": round(current_balance, 2),
            "scheduledHours": round(scheduled_hours, 2),
            "targetHours": round(target_hours, 2),
            "projectedBalance": round(projected_balance, 2),
            "fairnessDeviation": round(deviation, 2),
        }

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
            "totalObjectiveScore": len(assignments_solution) * 100,
            "employeeUtilization": employee_utilization,
            "employeeFairness": employee_fairness,
            "violations": violations,
        },
        "diagnostics": {
            "isOptimal": is_optimal,
            "info": info,
        },
    }
