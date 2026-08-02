from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.core.versioning import ConflictError, add_cache_headers, compute_etag, detect_conflict
from app.db.models.user import User
from app.dependencies import get_current_user, get_db, require_admin
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate
from app.services import role_service

router = APIRouter()


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return role_service.create_role(db, data)


@router.get("", response_model=PaginatedResponse[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
):
    total = db.query(role_service.Role).count()
    items = role_service.list_roles(db, offset=pagination.offset, limit=pagination.limit)
    return PaginatedResponse(items=items, total=total, offset=pagination.offset, limit=pagination.limit)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    response: Response = None,
):
    role = role_service.get_role_by_id(db, role_id)
    if not role:
        raise NotFoundException(detail="Role not found")
    if response is not None:
        etag = compute_etag(
            {
                "name": role.name,
                "color": role.color,
                "updated_at": str(role.updated_at),
            }
        )
        add_cache_headers(response, etag=etag, last_modified=role.updated_at)
    return role


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    if_match: str | None = Header(None, alias="If-Match"),
    response: Response = None,
):
    role = role_service.get_role_by_id(db, role_id)
    if not role:
        raise NotFoundException(detail="Role not found")
    role_etag = compute_etag(
        {
            "name": role.name,
            "color": role.color,
            "updated_at": str(role.updated_at),
        }
    )
    try:
        detect_conflict(role.updated_at, if_match, role_etag)
    except ConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role was modified by another user. Please refresh and try again.",
        )
    updated = role_service.update_role(db, role_id, data)
    if response is not None:
        new_etag = compute_etag(
            {
                "name": updated.name,
                "color": updated.color,
                "updated_at": str(updated.updated_at),
            }
        )
        add_cache_headers(response, etag=new_etag)
    return updated


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    role_service.delete_role(db, role_id)
