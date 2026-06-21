"""initial migration

Revision ID: 0001_initial
Revises: None
Create Date: 2026-05-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column(
            "username", sa.String(length=64), nullable=False, unique=True, index=True
        ),
        sa.Column(
            "email", sa.String(length=120), nullable=False, unique=True, index=True
        ),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("last_login", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("users")
