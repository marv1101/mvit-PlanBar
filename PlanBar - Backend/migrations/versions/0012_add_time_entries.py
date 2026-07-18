"""add time entries table

Revision ID: 0012
Revises: 0010
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "time_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("clock_in", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clock_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_time_entries_employee_id", "time_entries", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_time_entries_employee_id", table_name="time_entries")
    op.drop_table("time_entries")
