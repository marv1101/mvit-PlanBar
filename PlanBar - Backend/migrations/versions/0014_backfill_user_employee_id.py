"""backfill users.employee_id from employees.user_id

Legacy data only linked the reverse FK (employees.user_id), leaving
users.employee_id NULL, which broke planer team-scope. This backfills the
canonical column without overwriting existing links.

Revision ID: 0014
Revises: 0011
Create Date: 2026-08-01
"""

from alembic import op

revision = "0014"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET employee_id = emp.id
        FROM employees AS emp
        WHERE emp.user_id = users.id
          AND users.employee_id IS NULL
        """
    )


def downgrade() -> None:
    pass
