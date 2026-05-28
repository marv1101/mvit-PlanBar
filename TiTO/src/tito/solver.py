from collections import defaultdict
from typing import Any, Dict, List, Tuple, Union
from datetime import datetime, timedelta
import math
import logging
from ortools.sat.python.cp_model import CpModel, CpSolver, CpSolverStatus, LinearExpr

from .schema import JobPayload, ShiftTemplate, Requirement, Employee, Wish


def build_model(payload: Union[dict, JobPayload]) -> dict:
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
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    target = datetime.strptime(target_date_str, "%Y-%m-%d")
    return (target - start).days


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def _date_to_week_key(date_str: str) -> Tuple[int, int]:
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
    start_time = datetime.now()
    
    cp_model = CpModel()
    
    # Extrahiere Daten
    metadata = model.get("metadata", {})
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

    date_requirements: Dict[str, List[int]] = defaultdict(list)
    week_requirements: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for req_idx, requirement in enumerate(requirements):
        req_date = requirement.get("date")
        if req_date:
            date_requirements[req_date].append(req_idx)
            week_requirements[_date_to_week_key(req_date)].append(req_idx)

    unique_dates = sorted(date_requirements.keys())
    horizon_days = 0
    if unique_dates:
        horizon_days = (_parse_date(unique_dates[-1]) - _parse_date(unique_dates[0])).days + 1

    # Erstelle Decision Variables
    # assignment[emp_id, req_idx] = 1 wenn Mitarbeiter emp_id zu Requirement req_idx zugewiesen
    assignments = {}
    for emp_idx, employee in enumerate(employees):
        for req_idx, requirement in enumerate(requirements):
            assignments[(emp_idx, req_idx)] = cp_model.new_bool_var(
                f"assign_emp{emp_idx}_req{req_idx}"
            )
    
    # Constraint 1: Skill- und Verfügbarkeitsprüfung
    for req_idx, requirement in enumerate(requirements):
        needed_skills = requirement.get("neededSkills") or {}
        valid_employees = []
        
        for emp_idx, employee in enumerate(employees):
            date = requirement.get("date")
            # Prüfe ob Mitarbeiter verfügbar ist
            if date in (employee.get("forbiddenDates") or []):
                continue
            
            # Prüfe Skills
            employee_skills = set(employee.get("skills") or [])
            has_required_skills = all(
                skill in employee_skills for skill in needed_skills.keys()
            )
            if not has_required_skills:
                continue

            # Rollentrennung: Wenn ein Skill mit "ROLE_" beginnt, wird er als Rollenanforderung gewertet.
            role_required = None
            for skill in needed_skills.keys():
                if skill.startswith("ROLE_"):
                    role_required = skill.replace("ROLE_", "")
                    break

            if role_required and employee.get("role") != role_required:
                continue

            valid_employees.append(emp_idx)

        requirement_assignments = [
            assignments[(ei, req_idx)]
            for ei in valid_employees
        ]
        if requirement_assignments:
            cp_model.add(LinearExpr.sum(requirement_assignments) >= 1)
    
    # Constraint 2: Fairness - Schichten gleichmäßig auf alle Workers verteilen
    # Berechne min/max Schichten pro Worker (Zielbereich)
    total_shifts = len(requirements)
    num_workers = len(employees)
    
    if num_workers > 0 and total_shifts > 0:
        avg_shifts = total_shifts / num_workers
        min_shifts = int(avg_shifts)
        max_shifts = int(avg_shifts) + 1
        
        for emp_idx in range(num_workers):
            emp_shift_count = LinearExpr.sum([
                assignments[(emp_idx, req_idx)]
                for req_idx in range(len(requirements))
            ])
            # Worker sollte zwischen min_shifts und max_shifts Schichten haben
            cp_model.add(emp_shift_count >= min_shifts)
            cp_model.add(emp_shift_count <= max_shifts)
    
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
                    
                    # Berechne Ruhezeit zwischen den Schichten
                    # Fall 1: req_i endet vor req_j
                    rest_ij = _date_to_days(date_i, date_j) * 24 * 60 + (start_j - end_i)
                    # Fall 2: req_j endet vor req_i
                    rest_ji = _date_to_days(date_j, date_i) * 24 * 60 + (start_i - end_j)
                    
                    # Wenn eine der Ruhezeiten kleiner als min_rest_minutes ist,
                    # können nicht beide Requirements diesem Mitarbeiter zugewiesen werden
                    if rest_ij < min_rest_minutes and rest_ji < min_rest_minutes:
                        # Beide Kombinationen würden die Ruhezeit verletzen
                        cp_model.add(
                            assignments[(emp_idx, req_i)] + assignments[(emp_idx, req_j)] <= 1
                        )
                    elif rest_ij < min_rest_minutes:
                        # Nur wenn req_i vor req_j liegt, gibt es eine Verletzung
                        cp_model.add(
                            assignments[(emp_idx, req_i)] + assignments[(emp_idx, req_j)] <= 1
                        )

    # Neue Constraints: Tagesarbeitszeit, Sonntagsruhe, max. aufeinanderfolgende Tage und Wochenstunden
    works_on_date = {}
    daily_max_minutes = int(max_daily_hours * 60)
    sunday_dates = [date for date in unique_dates if _is_sunday(date)]
    if horizon_days > 0:
        required_free_sundays = int(math.ceil(min_free_sundays_per_year * (horizon_days / 365.0)))
    else:
        required_free_sundays = 0
    allowed_sunday_workdays = max(0, len(sunday_dates) - required_free_sundays)

    for emp_idx, employee in enumerate(employees):
        for date, req_indices in date_requirements.items():
            works_on_date[(emp_idx, date)] = cp_model.new_bool_var(
                f"works_emp{emp_idx}_{date}"
            )
            cp_model.add(
                sum(assignments[(emp_idx, req_idx)] for req_idx in req_indices)
                >= works_on_date[(emp_idx, date)]
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

        # Sonntagsruhe als harter Constraint
        #if sunday_dates:
        #    sunday_work_flags = [works_on_date[(emp_idx, date)] for date in sunday_dates]
        #    cp_model.add(LinearExpr.sum(sunday_work_flags) <= allowed_sunday_workdays)

        # Maximal aufeinanderfolgende Arbeitstage
        if max_consecutive_days > 0 and len(unique_dates) > max_consecutive_days:
            for index in range(len(unique_dates) - max_consecutive_days):
                window = unique_dates[index : index + max_consecutive_days + 1]
                cp_model.add(
                    LinearExpr.sum(
                        [works_on_date[(emp_idx, date)] for date in window]
                    )
                    <= max_consecutive_days
                )

        # Wochenarbeitszeit basierend auf Vertrag
        weekly_hours = float(
            (employee.get("contract") or {}).get("weeklyHours", default_weekly_hours)
        )
        weekly_limit_minutes = int(weekly_hours * 60)
        for week_key, req_indices in week_requirements.items():
            weekly_minutes = []
            for req_idx in req_indices:
                requirement = requirements[req_idx]
                shift = shift_templates.get(requirement.get("shiftId"), {})
                weekly_minutes.append(
                    assignments[(emp_idx, req_idx)] * _effective_shift_minutes(shift, employee)
                )
            if weekly_minutes:
                cp_model.add(LinearExpr.sum(weekly_minutes) <= weekly_limit_minutes)

        # Rotationsregeln: Vermeidung von Monotonie (z.B. nicht mehr als 3 Tage hintereinander die gleiche Schicht)
        # Wir implementieren eine einfache Regel: Max 3 gleiche Schichten in Folge
        max_same_shift_consecutive = 3
        for shift_id in shift_templates.keys():
            # Finde alle Requirements für diese Schicht
            shift_reqs = [i for i, r in enumerate(requirements) if r.get("shiftId") == shift_id]
            if len(shift_reqs) > max_same_shift_consecutive:
                # Wir müssen die Daten sortieren, um "aufeinanderfolgend" zu prüfen
                # Da unique_dates bereits sortiert ist, nutzen wir das.
                # Wir erstellen eine Liste von (datum, req_idx) für diese Schicht
                shift_dates_reqs = []
                for d in unique_dates:
                    for r_idx in date_requirements[d]:
                        if requirements[r_idx].get("shiftId") == shift_id:
                            shift_dates_reqs.append(r_idx)
                
                # Prüfe Fenster von max_same_shift_consecutive + 1 Tagen
                # Achtung: Das ist komplex, da ein Mitarbeiter an einem Tag mehrere Schichten haben könnte.
                # Wir vereinfachen: Wenn er an X Tagen hintereinander die gleiche Schicht-ID hat.
                for i in range(len(unique_dates) - max_same_shift_consecutive):
                    window_dates = unique_dates[i : i + max_same_shift_consecutive + 1]
                    window_assignments = []
                    for d in window_dates:
                        # Falls es mehrere Requirements der gleichen Schicht am selben Tag gibt,
                        # nehmen wir die Summe der Zuweisungen für diesen Mitarbeiter
                        day_reqs = [assignments[(emp_idx, r_idx)] for r_idx in date_requirements[d] 
                                    if requirements[r_idx].get("shiftId") == shift_id]
                        if day_reqs:
                            # Wir brauchen eine Variable, die 1 ist, wenn er an diesem Tag diese Schicht macht
                            # Da er pro Tag meist nur eine Schicht macht, ist die Summe okay, 
                            # aber wir müssen sicherstellen, dass es ein Bool-Wert bleibt.
                            # Wir nutzen eine Hilfsvariable.
                            day_works_shift = cp_model.new_bool_var(f"emp{emp_idx}_date{d}_shift{shift_id}")
                            cp_model.add(LinearExpr.sum(day_reqs) >= day_works_shift)
                            for var in day_reqs:
                                cp_model.add(var <= day_works_shift)
                            window_assignments.append(day_works_shift)
                        else:
                            window_assignments.append(0)
                    
                    if len(window_assignments) > max_same_shift_consecutive:
                        cp_model.add(LinearExpr.sum(window_assignments) <= max_same_shift_consecutive)


    # Constraint 4: Wünsche als weiche Constraints
    wish_penalty_vars = []
    for wish in wishes:
        wish_type = wish.get("type", "")
        employee_id = wish.get("employeeId")
        weight = wish.get("weight", 1)
        
        emp_idx = next(
            (i for i, e in enumerate(employees) if e.get("id") == employee_id),
            None
        )
        if emp_idx is None:
            continue
        
        if wish_type == "PREFER_SHIFT":
            date = wish.get("date")
            shift_id = wish.get("shiftId")
            
            # Finde passende Requirement
            matching_req = next(
                (i for i, r in enumerate(requirements)
                 if r.get("date") == date and r.get("shiftId") == shift_id),
                None
            )
            
            if matching_req is not None:
                # Variable ob Wunsch erfüllt ist
                wish_fulfilled = cp_model.new_bool_var(f"wish_fulfill_{emp_idx}_{date}_{shift_id}")
                cp_model.add(
                    wish_fulfilled == assignments[(emp_idx, matching_req)]
                )
                wish_penalty_vars.append((wish_fulfilled, weight))
    
    # Zielfunktion: Maximiere erfüllte Anforderungen und gewichtete Wünsche
    objective = []
    
    # Priorität: Anforderungen erfüllen
    for emp_idx, req_idx in assignments:
        objective.append(assignments[(emp_idx, req_idx)])
    
    # Sekundär: Wünsche erfüllen mit Gewichtung
    for wish_var, weight in wish_penalty_vars:
        objective.append(LinearExpr.sum([wish_var]) * weight)
    
    if objective:
        cp_model.maximize(LinearExpr.sum(objective))
    
    # Solver mit Timeout
    solver = CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.log_search_progress = False
    
    status = solver.Solve(cp_model)
    
    solve_time = (datetime.now() - start_time).total_seconds()
    
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
                    
                    assignments_solution.append({
                        "employeeId": employee["id"],
                        "date": date,
                        "shiftId": shift_id,
                        "startTime": shift.get("startTime", "00:00"),
                        "endTime": shift.get("endTime", "00:00"),
                    })
                    assigned = True
                    break
            
            if not assigned:
                unassigned_requirements.append(requirement)
                violations.append({
                    "type": "UNASSIGNED_REQUIREMENT",
                    "severity": "HARD",
                    "message": f"Requirement on {requirement.get('date')} with shift {requirement.get('shiftId')} could not be assigned",
                    "details": requirement
                })
    except Exception as e:
        # If no solution available (e.g., timeout without feasible solution)
        assignments_solution = []
        unassigned_requirements = requirements
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not extract solution: {e}")
    
    # Berechne Metriken
    try:
        fulfilled_wishes = sum(
            solver.Value(wish_var)
            for wish_var, _ in wish_penalty_vars
        )
        total_wishes = len(wish_penalty_vars)
        wish_rate = (
            100.0 if total_wishes == 0
            else round((fulfilled_wishes / total_wishes) * 100, 1)
        )
        
        # Wünsche als Soft-Constraint-Verletzungen tracken
        for wish in wishes:
            wish_type = wish.get("type", "")
            employee_id = wish.get("employeeId")
            
            emp_idx = next(
                (i for i, e in enumerate(employees) if e.get("id") == employee_id),
                None
            )
            if emp_idx is None: continue
            
            if wish_type == "PREFER_SHIFT":
                date = wish.get("date")
                shift_id = wish.get("shiftId")
                matching_req = next(
                    (i for i, r in enumerate(requirements)
                     if r.get("date") == date and r.get("shiftId") == shift_id),
                    None
                )
                if matching_req is not None:
                    if solver.Value(assignments[(emp_idx, matching_req)]) == 0:
                        violations.append({
                            "type": "WISH_NOT_FULFILLED",
                            "severity": "SOFT",
                            "message": f"Wish for employee {employee_id} on {date} (shift {shift_id}) not fulfilled",
                            "details": wish
                        })
    except Exception as e:
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
        if solver.BestObjectiveBound() > -float('inf'):
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
        
        # Finde Employee für individuelle Pause
        emp = next((e for e in employees if e["id"] == emp_id), {})
        employee_break = emp.get("breakMinutes")
        
        start_min = _time_to_minutes(shift.get("startTime", "00:00"))
        end_min = _time_to_minutes(shift.get("endTime", "00:00"))
        shift_hours = (end_min - start_min) / 60.0
        
        # Berechne effektive Arbeitszeit (minus Pause)
        break_hours = (employee_break or 0) / 60.0
        effective_hours = shift_hours - break_hours
        
        employee_utilization[emp_id] = employee_utilization.get(emp_id, 0.0) + effective_hours
    
    return {
        "metadata": {
            "status": solver_status,
            "solveTimeSeconds": round(solve_time, 2),
            "timestamp": datetime.now().isoformat() + "Z",
        },
        "solution": {
            "assignments": assignments_solution,
            "unassignedRequirements": unassigned_requirements,
        },
        "metrics": {
            "wishFulfillmentRate": wish_rate,
            "totalObjectiveScore": len(assignments_solution) * 100,
            "employeeUtilization": employee_utilization,
            "violations": violations,
        },
        "diagnostics": {
            "isOptimal": is_optimal,
            "info": info,
        },
    }
