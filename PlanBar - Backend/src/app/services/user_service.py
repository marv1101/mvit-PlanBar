from sqlalchemy.orm import Session

from app.core.auth import generate_password, hash_password, verify_password
from app.db.models.employee import Employee
from app.db.models.user import User
from app.schemas.user import AdminUserCreate, UserCreate, UserUpdate


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


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.id).all()


def update_user(db: Session, user: User, user_update: UserUpdate) -> User:
    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.password is not None:
        user.password_hash = hash_password(user_update.password)
    if user_update.role is not None:
        user.role = user_update.role
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def change_password(db: Session, user: User, old_password: str, new_password: str) -> User:
    if not verify_password(old_password, user.password_hash):
        raise ValueError("Old password is incorrect")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def admin_create_user(db: Session, admin_user: AdminUserCreate) -> tuple[User, str]:
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

    return user, password
