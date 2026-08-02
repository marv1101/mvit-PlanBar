"""add teams and employee_teams tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_teams_name", "teams", ["name"], unique=True)

    op.create_table(
        "employee_teams",
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("employee_teams")
    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_table("teams")
