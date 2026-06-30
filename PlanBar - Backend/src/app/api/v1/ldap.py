from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db, require_admin
from app.db.models.user import User
from app.schemas.ldap import LDAPStatusResponse, LDAPSyncResult, LDAPTestResult
from app.services import ldap_service

router = APIRouter()


@router.post("/test", response_model=LDAPTestResult)
def test_ldap_connection(admin: User = Depends(require_admin)):
    result = ldap_service.ldap_test_connection()
    return LDAPTestResult(**result)


@router.post("/sync", response_model=LDAPSyncResult)
def sync_ldap_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = ldap_service.ldap_sync_all(db)
    return LDAPSyncResult(**result)


@router.get("/status", response_model=LDAPStatusResponse)
def ldap_status(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return LDAPStatusResponse(
        enabled=settings.ldap_enabled,
        server=settings.ldap_server,
        user_search_base=settings.ldap_user_search_base,
        group_search_base=settings.ldap_group_search_base,
        use_tls=settings.ldap_use_tls,
        last_sync=ldap_service._get_last_sync_time(db),
    )
