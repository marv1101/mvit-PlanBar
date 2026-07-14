from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.db.models.user import User
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.role import RoleCreate, RoleUpdate
from app.services import role_service

router = APIRouter()


class RoleResponse(BaseModel):
    id: int
    name: str
    color: str | None = None
    permissions: str | None = None

    model_config = {"from_attributes": True}


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


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return role_service.update_role(db, role_id, data)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    role_service.delete_role(db, role_id)
