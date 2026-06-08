"""add manual_adjustment to timecard

Revision ID: 0003_add_manual_adjustment_to_timecard
Revises: 0002_add_shiftplan_unique_constraint
Create Date: 2026-06-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_add_manual_adjustment_to_timecard"
down_revision = "0002_add_shiftplan_unique_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("timecards", sa.Column("manual_adjustment", sa.Float(), nullable=False, server_default="0.0"))


def downgrade() -> None:
    op.drop_column("timecards", "manual_adjustment")
