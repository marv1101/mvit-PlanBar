"""add manual_adjustment_hours and adjustment_reason to timecards

Revision ID: 0003_add_manual_adjustment_to_timecard
Revises: 0002_add_shiftplan_unique_constraint
Create Date: 2026-06-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_add_manual_adjustment_to_timecard"
down_revision = "0002_add_shiftplan_unique_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "timecards",
        sa.Column("manual_adjustment_hours", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column("timecards", sa.Column("adjustment_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("timecards", "adjustment_reason")
    op.drop_column("timecards", "manual_adjustment_hours")
