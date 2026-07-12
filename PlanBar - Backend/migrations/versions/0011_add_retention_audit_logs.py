"""add retention audit logs

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retention_audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("record_id", sa.String(100), nullable=False),
        sa.Column("reason", sa.String(100), nullable=False),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.Column("executed_by", sa.String(64), nullable=False, server_default="system"),
    )
    op.create_index("ix_retention_audit_logs_category", "retention_audit_logs", ["category"])
    op.create_index("ix_retention_audit_logs_executed_at", "retention_audit_logs", ["executed_at"])


def downgrade() -> None:
    op.drop_index("ix_retention_audit_logs_executed_at", table_name="retention_audit_logs")
    op.drop_index("ix_retention_audit_logs_category", table_name="retention_audit_logs")
    op.drop_table("retention_audit_logs")
