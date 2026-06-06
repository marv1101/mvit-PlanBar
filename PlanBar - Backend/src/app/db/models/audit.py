from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class DeletionAuditLog(Base):
    """Audit log for GDPR deletion events.

    Stores ONLY non-personal data: user ID, timestamp, and deletion type.
    No email, username, or other PII is stored here.
    """

    __tablename__ = "deletion_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    deleted_user_id = Column(Integer, nullable=False, index=True)
    deleted_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    deletion_type = Column(
        Text, nullable=False, default="self_service"
    )  # "self_service" or "admin"
