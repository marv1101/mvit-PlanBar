from sqlalchemy.orm import Session

from app.core.auth import generate_password, hash_password, verify_password
from app.db.models.employee import Employee
from app.db.models.user import User
from app.schemas.user import AdminUserCreate, UserCreate, UserUpdate
from app.services import audit_service
from app.services.employee_service import _set_employee_teams


def create_user(db: Session, user_in: UserCreate, role: str = "user") -> User:
    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=role,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit_service.log_create(db, user_id=None, resource_type="user", resource_id=str(user.id))
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def list_users(db: Session, offset: int = 0, limit: int | None = None) -> list[User]:
    query = db.query(User).order_by(User.id)
    if limit is not None:
        query = query.offset(offset).limit(limit)
    return query.all()


def update_user(db: Session, user: User, user_update: UserUpdate, actor_id: int | None = None) -> User:
    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.password is not None:
        user.password_hash = hash_password(user_update.password)
    if user_update.role is not None:
        user.role = user_update.role

    if user_update.employee_id is not None:
        if user_update.employee_id == 0:
            if user.employee_id:
                old_emp = db.query(Employee).filter(Employee.id == user.employee_id).first()
                if old_emp and old_emp.user_id == user.id:
                    old_emp.user_id = None
                    db.add(old_emp)
            user.employee_id = None
        else:
            employee = db.query(Employee).filter(Employee.id == user_update.employee_id).first()
            if employee:
                employee.user_id = user.id
                db.add(employee)

    db.add(user)
    db.commit()
    db.refresh(user)

    if user_update.team_ids is not None and user.employee_id:
        employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if employee:
            _set_employee_teams(db, employee, user_update.team_ids)
            db.commit()

    audit_service.log_update(db, user_id=actor_id, resource_type="user", resource_id=str(user.id))
    return user


def delete_user(db: Session, user: User, actor_id: int | None = None) -> None:
    db.delete(user)
    db.commit()
    audit_service.log_delete(db, user_id=actor_id, resource_type="user", resource_id=str(user.id))


def change_password(db: Session, user: User, old_password: str, new_password: str) -> User:
    if not verify_password(old_password, user.password_hash):
        raise ValueError("Old password is incorrect")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def admin_create_user(db: Session, admin_user: AdminUserCreate, actor_id: int | None = None) -> tuple[User, str]:
    password = generate_password()
    user = User(
        username=admin_user.username,
        email=admin_user.email,
        password_hash=hash_password(password),
        role=admin_user.role,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if admin_user.employee_id is not None:
        employee = db.query(Employee).filter(Employee.id == admin_user.employee_id).first()
        if employee:
            employee.user_id = user.id
            db.add(employee)
            db.commit()

            if admin_user.team_ids is not None:
                _set_employee_teams(db, employee, admin_user.team_ids)
                db.commit()

    audit_service.log_create(
        db,
        user_id=actor_id,
        resource_type="user",
        resource_id=str(user.id),
        details=f"admin_created role={admin_user.role}",
    )
    return user, password
