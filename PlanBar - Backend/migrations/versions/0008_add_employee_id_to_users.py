"""add employee_id column to users table

Revision ID: 0008_add_employee_id_to_users
Revises: 0007_add_shiftplan_label
Create Date: 2026-06-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_add_employee_id_to_users"
down_revision = "0007_add_shiftplan_label"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("employee_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_employee_id",
        "users",
        "employees",
        ["employee_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_employee_id", "users", type_="foreignkey")
    op.drop_column("users", "employee_id")
