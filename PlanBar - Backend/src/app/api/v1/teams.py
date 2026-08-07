from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.core.versioning import ConflictError, check_etag_conflict, set_etag_header, set_etag_response
from app.db.models.team import Team
from app.db.models.user import User
from app.dependencies import get_current_user, get_db, require_admin
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.team import (
    EmployeeTeamAssignment,
    TeamCreate,
    TeamResponse,
    TeamUpdate,
    TeamWithEmployeesResponse,
)
from app.services import team_service

router = APIRouter()


def _team_with_employees(team: Team) -> TeamWithEmployeesResponse:
    return TeamWithEmployeesResponse(
        id=team.id,
        name=team.name,
        color=team.color,
        description=team.description,
        employee_ids=[e.id for e in team.employees],
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team_endpoint(
    data: TeamCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return team_service.create_team(db, data, actor_id=admin.id)


@router.get("", response_model=PaginatedResponse[TeamResponse])
def list_teams_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    """List teams.

    Admins see all teams. Planners/employees get a paginated list of their own
    teams via /teams/mine; this endpoint still returns their own teams filtered
    accordingly to keep the API simple for clients calling /teams.
    """
    if current_user.role == "admin":
        total = db.query(Team).count()
        items = team_service.list_teams(db, offset=pagination.offset, limit=pagination.limit)
    else:
        teams = team_service.get_teams_for_user(db, current_user)
        total = len(teams)
        items = teams[pagination.offset : pagination.offset + pagination.limit]
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)


@router.get("/mine", response_model=list[TeamResponse])
def list_my_teams_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List teams the current user belongs to (for planners/employees)."""
    # Admins also can call this and will receive [] (no team restriction).
    return team_service.get_teams_for_user(db, current_user)


@router.get("/{team_id}", response_model=TeamWithEmployeesResponse)
def get_team_endpoint(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    response: Response = None,
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise NotFoundException(detail="Team not found")
    if current_user.role != "admin" and team not in team_service.get_teams_for_user(db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    if response is not None:
        set_etag_header(response, team, "name", "color")
    return _team_with_employees(team)


@router.put("/{team_id}", response_model=TeamResponse)
def update_team_endpoint(
    team_id: int,
    data: TeamUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    if_match: str | None = Header(None, alias="If-Match"),
    response: Response = None,
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise NotFoundException(detail="Team not found")
    try:
        check_etag_conflict(team, if_match, "name", "color")
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Team was modified by another user. Please refresh and try again.",
        ) from e
    updated = team_service.update_team(db, team_id, data, actor_id=admin.id)
    if response is not None:
        set_etag_response(response, updated, "name", "color")
    return updated


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team_endpoint(
    team_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    team_service.delete_team(db, team_id, actor_id=admin.id)


@router.post("/{team_id}/employees", response_model=TeamWithEmployeesResponse)
def assign_team_employees_endpoint(
    team_id: int,
    data: EmployeeTeamAssignment,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    team = team_service.assign_employees(db, team_id, data.employee_ids, actor_id=admin.id)
    return _team_with_employees(team)
