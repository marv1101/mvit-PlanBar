from typing import Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.models.user import User


class SyncActionRegistry:
    _by_key: dict[tuple[str, str], Any] = {}

    @classmethod
    def register(cls, action: Any) -> None:
        cls._by_key[(action.resource, action.action)] = action

    @classmethod
    def get(cls, resource: str, action: str) -> Any:
        if (resource, action) not in cls._by_key:
            raise HTTPException(status_code=400, detail=f"Unsupported action: {resource}/{action}")
        return cls._by_key[(resource, action)]

    @classmethod
    def dispatch(cls, payload: Any, db: Session, user: User) -> dict[str, Any]:
        handler = cls.get(payload.resource, payload.action)
        handler.role.check(user)
        return handler.execute(db, payload.data, user)

    @classmethod
    def reset(cls) -> None:
        cls._by_key.clear()
