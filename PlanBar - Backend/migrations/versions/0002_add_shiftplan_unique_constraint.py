"""add unique constraint on shiftplans

Revision ID: 0002_add_shiftplan_unique_constraint
Revises: 0001_initial
Create Date: 2026-06-01 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_shiftplan_unique_constraint"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_shiftplan_schedule_employee_date_shift",
        "shiftplans",
        ["schedule_id", "employee_id", "date", "shift_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_shiftplan_schedule_employee_date_shift",
        "shiftplans",
        type_="unique",
    )
