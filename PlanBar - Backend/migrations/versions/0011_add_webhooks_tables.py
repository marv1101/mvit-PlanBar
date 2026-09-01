"""add webhooks tables

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-01
"""

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("secret", sa.String(length=128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhooks_id"), "webhooks", ["id"])

    op.create_table(
        "webhook_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("webhook_id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("request_url", sa.String(length=512), nullable=False),
        sa.Column("request_body", sa.Text(), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("dead_letter", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["webhook_id"], ["webhooks.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_logs_id"), "webhook_logs", ["id"])
    op.create_index(op.f("ix_webhook_logs_webhook_id"), "webhook_logs", ["webhook_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_webhook_logs_webhook_id"), table_name="webhook_logs")
    op.drop_index(op.f("ix_webhook_logs_id"), table_name="webhook_logs")
    op.drop_table("webhook_logs")
    op.drop_index(op.f("ix_webhooks_id"), table_name="webhooks")
    op.drop_table("webhooks")
