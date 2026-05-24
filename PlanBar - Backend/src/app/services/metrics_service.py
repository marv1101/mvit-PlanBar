from typing import Any

from sqlalchemy.orm import Session

from app.db.models.schedule import Schedule


def get_aggregated_metrics(db: Session) -> dict[str, Any]:
    schedules = db.query(Schedule).filter(Schedule.status == "completed").all()

    total_schedules = len(schedules)
    total_solve_time = 0.0
    total_wish_fulfillment = 0.0
    completed_count = 0

    for schedule in schedules:
        if schedule.metrics_json:
            total_solve_time += schedule.metrics_json.get("solveTimeSeconds", 0)
            wish_rate = schedule.metrics_json.get("wishFulfillmentRate")
            if wish_rate is not None:
                total_wish_fulfillment += wish_rate
                completed_count += 1

    return {
        "total_schedules": total_schedules,
        "average_solve_time": round(total_solve_time / max(total_schedules, 1), 2),
        "average_wish_fulfillment_rate": round(total_wish_fulfillment / max(completed_count, 1), 2),
        "completed_schedules": completed_count,
        "failed_schedules": db.query(Schedule).filter(Schedule.status == "failed").count(),
        "draft_schedules": db.query(Schedule).filter(Schedule.status == "draft").count(),
    }


def get_robustness_metrics(db: Session) -> dict[str, Any]:
    completed = db.query(Schedule).filter(Schedule.status == "completed").all()

    optimal_count = 0
    for schedule in completed:
        if schedule.diagnostics_json and schedule.diagnostics_json.get("isOptimal"):
            optimal_count += 1

    return {
        "total_optimal": optimal_count,
        "total_completed": len(completed),
        "optimal_rate": round(optimal_count / max(len(completed), 1) * 100, 2),
    }
