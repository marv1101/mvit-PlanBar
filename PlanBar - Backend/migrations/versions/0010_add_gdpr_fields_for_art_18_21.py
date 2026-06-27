"""add gdpr fields for art 18 21

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("processing_restricted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "users",
        sa.Column("objection_filed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "users",
        sa.Column("objection_date", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "employees",
        sa.Column("processing_restricted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("employees", "processing_restricted")
    op.drop_column("users", "objection_date")
    op.drop_column("users", "objection_filed")
    op.drop_column("users", "processing_restricted")
