"""add pinboard tables

Revision ID: 0004_add_pinboard_tables
Revises: 0003_add_manual_adjustment_to_timecard
Create Date: 2026-06-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_pinboard_tables"
down_revision = "0003_add_manual_adjustment_to_timecard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pinboard_threads",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_table(
        "pinboard_messages",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column(
            "thread_id",
            sa.Integer(),
            sa.ForeignKey("pinboard_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_table(
        "pinboard_documents",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column(
            "message_id",
            sa.Integer(),
            sa.ForeignKey("pinboard_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
    )


def downgrade() -> None:
    op.drop_table("pinboard_documents")
    op.drop_table("pinboard_messages")
    op.drop_table("pinboard_threads")
