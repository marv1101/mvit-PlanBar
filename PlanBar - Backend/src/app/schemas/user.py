import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_password_complexity(value: str) -> str:
    """
    Validate password meets complexity requirements.

    BSI IT-Grundschutz recommends:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    """
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter")

    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one digit")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', value):
        raise ValueError("Password must contain at least one special character")

    return value


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_complexity(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    # Note: Password complexity is NOT validated on login
    # because users may have old passwords that predate complexity requirements


class TokenRefreshRequest(BaseModel):
    refresh_token: str | None = Field(None, min_length=10)


class UserUpdate(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=64)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8)
    role: str | None = Field(None, pattern=r"^(admin|user|planer)$")
    employee_id: int | None = None
    team_ids: list[int] | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_password_complexity(v)
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    must_change_password: bool = True
    employee_id: int | None = None
    processing_restricted: bool = False
    objection_filed: bool = False
    objection_date: datetime | None = None
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - "bearer" is a token type, not a password


class LoginResponse(TokenResponse):
    must_change_password: bool = True


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_complexity(v)


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    role: str = Field(default="user", pattern="^(admin|user|planer)$")
    employee_id: int | None = None
    team_ids: list[int] = []


class AdminUserCreateResponse(UserResponse):
    initial_password: str
