"""add label column to shiftplans table

Revision ID: 0007_add_shiftplan_label
Revises: 0006_add_schedule_shift_templates
Create Date: 2026-06-15 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_add_shiftplan_label"
down_revision = "0006_add_schedule_shift_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shiftplans", sa.Column("label", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("shiftplans", "label")
