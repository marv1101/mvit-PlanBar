from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.db.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate
from app.services import audit_service


def list_roles(db: Session, offset: int = 0, limit: int | None = None) -> list[Role]:
    query = db.query(Role).order_by(Role.name)
    if limit is not None:
        query = query.offset(offset).limit(limit)
    return query.all()


def get_role_by_id(db: Session, role_id: int) -> Role | None:
    return db.query(Role).filter(Role.id == role_id).first()


def create_role(db: Session, data: RoleCreate, actor_id: int | None = None) -> Role:
    role = Role(name=data.name, color=data.color, permissions=data.permissions)
    db.add(role)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ConflictException(detail="Role with this name already exists") from e
    db.refresh(role)
    audit_service.log_create(db, user_id=actor_id, resource_type="role", resource_id=str(role.id))
    return role


def update_role(
    db: Session,
    role_id: int,
    data: RoleUpdate,
    actor_id: int | None = None,
) -> Role:
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise NotFoundException(detail="Role not found")
    if data.name is not None:
        role.name = data.name
    if data.color is not None:
        role.color = data.color
    if data.permissions is not None:
        role.permissions = data.permissions
    db.add(role)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ConflictException(detail="Role with this name already exists") from e
    db.refresh(role)
    audit_service.log_update(db, user_id=actor_id, resource_type="role", resource_id=str(role.id))
    return role


def delete_role(db: Session, role_id: int, actor_id: int | None = None) -> None:
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise NotFoundException(detail="Role not found")
    db.delete(role)
    db.commit()
    audit_service.log_delete(db, user_id=actor_id, resource_type="role", resource_id=str(role_id))
