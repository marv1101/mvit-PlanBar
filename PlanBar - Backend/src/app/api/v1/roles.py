from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.dependencies import get_current_user, get_db, require_admin
from app.db.models.role import Role
from app.db.models.user import User

router = APIRouter()


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    permissions: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    permissions: str | None = None


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
    existing = db.query(Role).filter(Role.name == data.name).first()
    if existing:
        raise ConflictException(detail="Role with this name already exists")
    role = Role(name=data.name, color=data.color, permissions=data.permissions)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Role).order_by(Role.name).all()


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise NotFoundException(detail="Role not found")
    if data.name is not None:
        existing = (
            db.query(Role).filter(Role.name == data.name, Role.id != role_id).first()
        )
        if existing:
            raise ConflictException(detail="Role with this name already exists")
        role.name = data.name
    if data.color is not None:
        role.color = data.color
    if data.permissions is not None:
        role.permissions = data.permissions
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise NotFoundException(detail="Role not found")
    db.delete(role)
    db.commit()
