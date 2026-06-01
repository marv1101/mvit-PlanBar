import logging
from datetime import time

from sqlalchemy.orm import Session

from app.db.models.employee import Employee
from app.db.models.schedule import Schedule, Shiftplan
from app.schemas.tito import TiTOCallbackPayload

logger = logging.getLogger(__name__)


def process_tito_callback(db: Session, payload: TiTOCallbackPayload) -> Schedule | None:
    schedule = db.query(Schedule).filter(Schedule.tito_job_id == payload.job_id).first()
    if not schedule:
        return None

    schedule.status = "completed" if payload.status.upper() in ("SUCCESS", "FEASIBLE", "COMPLETED") else "failed"
    schedule.metadata_json = payload.metadata.model_dump() if payload.metadata else None
    schedule.metrics_json = payload.metrics.model_dump() if payload.metrics else None
    schedule.diagnostics_json = payload.diagnostics.model_dump() if payload.diagnostics else None

    if payload.solution and payload.solution.assignments:
        db.query(Shiftplan).filter(Shiftplan.schedule_id == schedule.id).delete()

        for assignment in payload.solution.assignments:
            employee = db.query(Employee).filter(
                Employee.id == _extract_employee_id(assignment.employeeId)
            ).first()

            if not employee:
                continue

            start_parts = assignment.startTime.split(":")
            end_parts = assignment.endTime.split(":")

            shiftplan = Shiftplan(
                schedule_id=schedule.id,
                employee_id=employee.id,
                date=assignment.date,
                shift_id=assignment.shiftId,
                week=schedule.week_type,
                start_time=time(int(start_parts[0]), int(start_parts[1])),
                end_time=time(int(end_parts[0]), int(end_parts[1])),
            )
            db.add(shiftplan)

    db.commit()
    db.refresh(schedule)
    return schedule


def _extract_employee_id(employee_id_str: str) -> int:
    try:
        return int(employee_id_str.replace("emp_", ""))
    except (ValueError, AttributeError):
        logger.exception("Could not extract employee ID from '%s'", employee_id_str)
        return 0
