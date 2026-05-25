from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.core.auth import create_access_token, create_refresh_token, verify_token
from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.db.models.user import User
from app.schemas.user import (
    TokenRefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.services.user_service import (
    authenticate_user,
    create_user,
    delete_user,
    get_user_by_id,
    list_users,
    update_user,
)

router = APIRouter()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter((User.email == user_in.email) | (User.username == user_in.username)).first()
    if existing:
        raise ConflictException(detail="User with email or username already exists")
    user = create_user(db, user_in)
    return user


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise UnauthorizedException(detail="Invalid email or password")
    user.last_login = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/refresh-token", response_model=TokenResponse)
def refresh_token(token_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = verify_token(token_data.refresh_token)
    except ValueError:
        raise UnauthorizedException(detail="Invalid refresh token")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedException(detail="Invalid refresh token payload")

    user = get_user_by_id(db, int(user_id))
    if user is None:
        raise NotFoundException(detail="User not found")

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("", response_model=list[UserResponse])
def list_users_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_users(db)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.id != user_id and current_user.role != "admin":
        raise UnauthorizedException(detail="Insufficient permissions")

    user = get_user_by_id(db, user_id)
    if user is None:
        raise NotFoundException(detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user_endpoint(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id != user_id and current_user.role != "admin":
        raise UnauthorizedException(detail="Insufficient permissions")

    user = get_user_by_id(db, user_id)
    if user is None:
        raise NotFoundException(detail="User not found")

    if user_in.email:
        existing = db.query(User).filter(User.email == user_in.email, User.id != user.id).first()
        if existing:
            raise ConflictException(detail="Email already in use")
    if user_in.username:
        existing = db.query(User).filter(User.username == user_in.username, User.id != user.id).first()
        if existing:
            raise ConflictException(detail="Username already in use")

    return update_user(db, user, user_in)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.id != user_id and current_user.role != "admin":
        raise UnauthorizedException(detail="Insufficient permissions")

    user = get_user_by_id(db, user_id)
    if user is None:
        raise NotFoundException(detail="User not found")

    delete_user(db, user)
    return None
