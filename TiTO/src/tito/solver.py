from typing import Any
from datetime import datetime, timedelta
from ortools.sat.python.cp_model import CpModel, CpSolver, CpSolverStatus, LinearExpr


def build_model(payload: dict) -> dict:
    """Übersetze das Eingabe-Payload in ein vorläufiges Modell."""
    model = {
        "metadata": payload.get("metadata", {}),
        "config": payload.get("config", {}),
        "shiftTemplates": {item["id"]: item for item in payload.get("shiftTemplates", [])},
        "requirements": payload.get("requirements", []),
        "employees": payload.get("employees", []),
        "wishes": payload.get("wishes", []),
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
    wishes = model.get("wishes", [])
    
    start_date = config.get("startDate", "2026-01-01")
    end_date = config.get("endDate", "2026-01-31")
    
    max_consecutive_days = config.get("maxConsecutiveDays", 6)
    min_rest_hours = config.get("minRestTimeHours", 11)
    
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
        needed_skills = requirement.get("neededSkills", {})
        valid_employees = []
        
        for emp_idx, employee in enumerate(employees):
            date = requirement.get("date")
            # Prüfe ob Mitarbeiter verfügbar ist
            if date in employee.get("forbiddenDates", []):
                continue
            
            # Prüfe Skills
            employee_skills = set(employee.get("skills", []))
            has_required_skills = all(
                skill in employee_skills for skill in needed_skills.keys()
            )
            
            if has_required_skills:
                valid_employees.append(emp_idx)
        
        # Nur gültige Mitarbeiter können zugewiesen werden
        for emp_idx in range(len(employees)):
            if emp_idx not in valid_employees:
                cp_model.add(assignments[(emp_idx, req_idx)] == 0)
        
        # WICHTIG: Jedes Requirement MUSS erfüllt werden (Hard Constraint)
        requirement_assignments = [
            assignments[(emp_idx, req_idx)]
            for emp_idx in valid_employees
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
    
    # Constraint 3: Wünsche als weiche Constraints
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
    
    # Berechne Metriken
    fulfilled_wishes = sum(
        solver.Value(wish_var)
        for wish_var, _ in wish_penalty_vars
    )
    total_wishes = len(wish_penalty_vars)
    wish_rate = (
        100.0 if total_wishes == 0
        else round((fulfilled_wishes / total_wishes) * 100, 1)
    )
    
    # Bestimme Status
    if status == CpSolverStatus.OPTIMAL:  # OPTIMAL
        solver_status = "SUCCESS"
        is_optimal = True
        info = "Optimale Lösung gefunden."
    elif status == CpSolverStatus.FEASIBLE:  # FEASIBLE
        solver_status = "FEASIBLE"
        is_optimal = False
        info = "Zulässige Lösung gefunden, aber nicht optimal."
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
            "jobId": metadata.get("jobId"),
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
            "violations": {
                "softConstraints": []
            }
        },
        "diagnostics": {
            "isOptimal": is_optimal,
            "info": info,
        },
    }
