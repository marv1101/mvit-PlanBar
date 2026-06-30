from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LDAPTestResult(BaseModel):
    success: bool
    message: str
    server_info: Optional[str] = None


class LDAPSyncResult(BaseModel):
    users_created: int = 0
    users_updated: int = 0
    errors: list[str] = []


class LDAPStatusResponse(BaseModel):
    enabled: bool
    server: str
    user_search_base: str
    group_search_base: str
    use_tls: bool
    last_sync: Optional[datetime] = None
