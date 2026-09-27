from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.db.models.employee import Employee
from app.db.models.schedule import Schedule, Shiftplan
from app.db.models.team import Team, employee_teams
from app.db.models.user import User
from app.schemas.kiosk import KioskBoardResponse, KioskEmployeeItem, KioskShiftItem, KioskTeamItem
from app.services import team_service

WINDOW_DAYS = 14


def compute_kiosk_window(today: date | None = None) -> tuple[date, date]:
    """Return the kiosk display window.

    Monday of the current ISO week through Sunday of the following week
    (``WINDOW_DAYS`` consecutive days). ``today`` is injectable for tests.
    """
    today = today or datetime.now(tz=timezone.utc).date()
    window_start = today - timedelta(days=today.weekday())
    window_end = window_start + timedelta(days=WINDOW_DAYS - 1)
    return window_start, window_end


def _resolve_team(db: Session, user: User, team_id: int | None) -> tuple[Team | None, list[int]]:
    """Resolve the selected team and the employee team scope for *user*.

    Returns ``(team, team_ids)`` where ``team`` is None when all teams are
    shown and ``team_ids`` holds the ids employees/shifts are filtered by
    (empty list = show everything).

    Raises ``NotFoundException`` for an unknown team and a 403
    ``HTTPException`` when a team-restricted user selects a team outside
    their scope.
    """
    # Kiosk and admin are role-unrestricted: any team (or all teams).
    if user.role in ("kiosk", "admin"):
        if team_id is None:
            return None, []
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise NotFoundException(detail="Team not found")
        return team, [team_id]

    # planer/user: a selected team must be inside their team scope.
    scope_ids = team_service.get_team_ids_for_user(db, user)
    if team_id is not None:
        if team_id not in scope_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Team is not in your team scope",
            )
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise NotFoundException(detail="Team not found")
        return team, [team_id]

    if scope_ids:
        return None, scope_ids

    # Fallback: user without employee link/teams sees all colleagues.
    return None, []


def get_kiosk_board(
    db: Session,
    user: User,
    team_id: int | None = None,
    today: date | None = None,
) -> KioskBoardResponse:
    """Build the read-only kiosk board payload for *user*.

    Shows shifts of completed schedules inside the 14-day window. When
    *team_id* is given only that team's employees/shifts are returned;
    otherwise the caller's team scope applies (kiosk/admin see everything).
    """
    window_start, window_end = compute_kiosk_window(today)

    team, team_ids = _resolve_team(db, user, team_id)

    query = (
        db.query(Shiftplan)
        .join(Schedule, Shiftplan.schedule_id == Schedule.id)
        .filter(Schedule.status == "completed", Shiftplan.date.between(window_start, window_end))
    )
    if team_ids:
        query = query.join(employee_teams, employee_teams.c.employee_id == Shiftplan.employee_id).filter(
            employee_teams.c.team_id.in_(team_ids)
        )
    shiftplans = query.order_by(Shiftplan.date.asc(), Shiftplan.start_time.asc()).all()

    schedule_ids = {sp.schedule_id for sp in shiftplans}
    schedule_names = (
        {s.id: s.name for s in db.query(Schedule).filter(Schedule.id.in_(schedule_ids)).all()} if schedule_ids else {}
    )

    employee_query = db.query(Employee)
    if team_ids:
        employee_query = employee_query.join(employee_teams, employee_teams.c.employee_id == Employee.id).filter(
            employee_teams.c.team_id.in_(team_ids)
        )
    employees = employee_query.order_by(Employee.first_name.asc(), Employee.last_name.asc()).all()

    return KioskBoardResponse(
        window_start=str(window_start),
        window_end=str(window_end),
        team=KioskTeamItem(id=team.id, name=team.name) if team else None,
        employees=[
            KioskEmployeeItem(
                id=e.id,
                name=f"{e.first_name} {e.last_name}",
                color=e.color,
            )
            for e in employees
        ],
        shifts=[
            KioskShiftItem(
                employee_id=sp.employee_id,
                date=str(sp.date),
                start_time=str(sp.start_time),
                end_time=str(sp.end_time),
                break_start=sp.break_start,
                break_end=sp.break_end,
                label=sp.label,
                schedule_name=schedule_names.get(sp.schedule_id, ""),
            )
            for sp in shiftplans
        ],
    )
