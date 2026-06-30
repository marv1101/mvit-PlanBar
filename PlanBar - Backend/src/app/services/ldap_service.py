import logging
from datetime import datetime, timezone
from typing import Optional

from ldap3 import ALL, Connection, Server
from sqlalchemy.orm import Session

from app.config import settings
from app.core.auth import generate_password, hash_password
from app.db.models.user import User
from app.services import audit_service

logger = logging.getLogger(__name__)


def _get_ldap_connection() -> Optional[Connection]:
    try:
        server = Server(settings.ldap_server, get_info=ALL)
        conn = Connection(
            server,
            user=settings.ldap_bind_dn,
            password=settings.ldap_bind_password,
            auto_bind=True,
        )
        if settings.ldap_use_tls:
            conn.start_tls()
        return conn
    except Exception as exc:
        logger.warning("LDAP connection failed: %s", exc)
        return None


def _map_ldap_role(entry) -> str:
    if not settings.ldap_role_mapping:
        return "user"
    member_of = getattr(entry, "memberOf", None)
    if not member_of:
        return "user"
    for group_dn in member_of:
        parts = [p.strip() for p in str(group_dn).split(",")]
        for part in parts:
            if part.upper().startswith("CN="):
                group_name = part[3:]
                if group_name in settings.ldap_role_mapping:
                    return settings.ldap_role_mapping[group_name]
    return "user"


def _get_last_sync_time(db: Session) -> Optional[datetime]:
    from app.db.models.audit_log import AuditLog

    entry = (
        db.query(AuditLog)
        .filter(AuditLog.action == "LDAP_SYNC")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    return entry.created_at if entry else None


def ldap_authenticate(db: Session, email: str, password: str) -> Optional[User]:
    if not settings.ldap_enabled:
        return None

    conn = _get_ldap_connection()
    if not conn:
        logger.warning("LDAP unavailable, falling back to local auth")
        return None

    try:
        search_filter = f"(&{settings.ldap_user_search_filter}(mail={email}))"
        conn.search(
            search_base=settings.ldap_user_search_base,
            search_filter=search_filter,
            attributes=["cn", "mail", "memberOf"],
        )

        if len(conn.entries) == 0:
            logger.info("LDAP user not found for email: %s", email)
            return None

        entry = conn.entries[0]
        user_dn = entry.entry_dn

        try:
            user_conn = Connection(
                Server(settings.ldap_server),
                user=user_dn,
                password=password,
                auto_bind=True,
            )
            user_conn.unbind()
        except Exception:
            logger.info("LDAP bind failed for %s", email)
            return None

        user = db.query(User).filter(User.email == email).first()
        if not user:
            username = str(entry.cn) if hasattr(entry, "cn") and entry.cn else email.split("@")[0]
            user = User(
                username=username,
                email=email,
                password_hash=hash_password(generate_password()),
                role=_map_ldap_role(entry),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            audit_service.log(
                db,
                user_id=user.id,
                action="LDAP_CREATED",
                resource_type="user",
                resource_id=str(user.id),
            )
        else:
            new_role = _map_ldap_role(entry)
            if new_role != user.role:
                user.role = new_role
                db.add(user)
                db.commit()
                audit_service.log(
                    db,
                    user_id=user.id,
                    action="LDAP_ROLE_UPDATED",
                    resource_type="user",
                    resource_id=str(user.id),
                    details=f"new_role={new_role}",
                )

        audit_service.log(
            db,
            user_id=user.id,
            action="LOGIN_LDAP",
            resource_type="user",
            resource_id=str(user.id),
        )
        return user

    finally:
        conn.unbind()


def ldap_sync_all(db: Session) -> dict:
    if not settings.ldap_enabled:
        return {"users_created": 0, "users_updated": 0, "errors": ["LDAP is disabled"]}

    conn = _get_ldap_connection()
    if not conn:
        return {"users_created": 0, "users_updated": 0, "errors": ["LDAP connection failed"]}

    result = {"users_created": 0, "users_updated": 0, "errors": []}

    try:
        conn.search(
            search_base=settings.ldap_user_search_base,
            search_filter=settings.ldap_user_search_filter,
            attributes=["cn", "mail", "memberOf"],
        )

        for entry in conn.entries:
            try:
                mail = str(entry.mail) if hasattr(entry, "mail") and entry.mail else None
                if not mail:
                    continue

                username = str(entry.cn) if hasattr(entry, "cn") and entry.cn else mail.split("@")[0]

                user = db.query(User).filter(User.email == mail).first()
                if not user:
                    user = User(
                        username=username,
                        email=mail,
                        password_hash=hash_password(generate_password()),
                        role=_map_ldap_role(entry),
                    )
                    db.add(user)
                    db.commit()
                    result["users_created"] += 1
                else:
                    new_role = _map_ldap_role(entry)
                    if new_role != user.role:
                        user.role = new_role
                        db.add(user)
                        db.commit()
                    result["users_updated"] += 1

            except Exception as exc:
                result["errors"].append(f"Error processing {entry.entry_dn}: {exc}")

        audit_service.log(
            db,
            user_id=None,
            action="LDAP_SYNC",
            resource_type="system",
            resource_id="ldap_sync",
            details=f"created={result['users_created']} updated={result['users_updated']} errors={len(result['errors'])}",
        )

    finally:
        conn.unbind()

    return result


def ldap_test_connection() -> dict:
    result = {"success": False, "message": "", "server_info": None}

    if not settings.ldap_enabled:
        result["message"] = "LDAP is disabled in configuration"
        return result

    try:
        server = Server(settings.ldap_server, get_info=ALL)
        conn = Connection(
            server,
            user=settings.ldap_bind_dn,
            password=settings.ldap_bind_password,
            auto_bind=True,
        )

        result["success"] = True
        result["message"] = "LDAP connection successful"
        result["server_info"] = str(server.info) if server.info else None

        conn.unbind()

    except Exception as exc:
        result["message"] = f"LDAP connection failed: {str(exc)}"

    return result
