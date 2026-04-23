from typing import Any


def build_model(payload: dict) -> dict:
    """Übersetze das Eingabe-Payload in ein vorläufiges Modell."""
    model = {
        "metadata": payload.get("metadata", {}),
        "shiftTemplates": {item["id"]: item for item in payload.get("shiftTemplates", [])},
        "requirements": payload.get("requirements", []),
        "employees": payload.get("employees", []),
        "wishes": payload.get("wishes", []),
    }
    return model


def solve_model(model: dict, timeout_seconds: int) -> dict:
    """Löse das Modell und generiere eine einfache Planlösung."""
    assignments = []
    unassigned = []
    shift_templates = model["shiftTemplates"]
    employees = model["employees"]
    wishes = model.get("wishes", [])
    wish_map = {
        (wish.get("employeeId"), wish.get("date"), wish.get("shiftId")): wish
        for wish in wishes
        if wish.get("type") == "PREFER_SHIFT"
    }

    for requirement in model["requirements"]:
        date = requirement.get("date")
        shift_id = requirement.get("shiftId")
        needed_skills = requirement.get("neededSkills", {})
        selected = None

        for employee in employees:
            if date in employee.get("forbiddenDates", []):
                continue
            employee_skills = set(employee.get("skills", []))
            if not employee_skills.intersection(needed_skills.keys()):
                continue
            selected = employee
            break

        if selected is None:
            unassigned.append(requirement)
            continue

        shift = shift_templates.get(shift_id, {})
        assignments.append(
            {
                "employeeId": selected["id"],
                "date": date,
                "shiftId": shift_id,
                "startTime": shift.get("startTime", "00:00"),
                "endTime": shift.get("endTime", "00:00"),
            }
        )

    fulfilled = 0
    total_wishes = 0
    for wish in wishes:
        if wish.get("type") != "PREFER_SHIFT":
            continue
        total_wishes += 1
        key = (wish.get("employeeId"), wish.get("date"), wish.get("shiftId"))
        if any(a["employeeId"] == wish.get("employeeId") and a["date"] == wish.get("date") and a["shiftId"] == wish.get("shiftId") for a in assignments):
            fulfilled += 1

    wish_rate = 100.0 if total_wishes == 0 else round((fulfilled / total_wishes) * 100, 1)
    status = "SUCCESS" if not unassigned else "FEASIBLE" if assignments else "INFEASIBLE"

    return {
        "metadata": {
            "jobId": model["metadata"].get("jobId"),
            "status": status,
            "solveTimeSeconds": 0.0,
        },
        "solution": {
            "assignments": assignments,
            "unassignedRequirements": unassigned,
        },
        "metrics": {
            "wishFulfillmentRate": wish_rate,
            "totalObjectiveScore": len(assignments) * 100,
        },
        "diagnostics": {
            "isOptimal": False,
            "info": "Einfache Zuordnung auf Basis verfügbarer Skills erstellt.",
        },
    }
