from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from app.db.base import Base


class RetentionAuditLog(Base):
    __tablename__ = "retention_audit_logs"

    id = Column(String(36), primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    action = Column(String(20), nullable=False)
    record_id = Column(String(100), nullable=False)
    reason = Column(String(100), nullable=False)
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    executed_by = Column(String(64), nullable=False, default="system")
