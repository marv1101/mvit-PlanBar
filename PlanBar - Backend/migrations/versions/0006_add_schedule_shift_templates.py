"""add shift_templates column to schedules table

Revision ID: 0006_add_schedule_shift_templates
Revises: 0005_add_audit_logs
Create Date: 2026-06-14 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_add_schedule_shift_templates"
down_revision = "0005_add_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("schedules", sa.Column("shift_templates", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("schedules", "shift_templates")
