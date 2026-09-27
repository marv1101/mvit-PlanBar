"""add ArbZG-relevant employee fields

is_minor, is_night_worker, night_worker_exam_date, protection_until,
is_shift_worker — used by the unified ArbZG/JArbSchG/MuSchG validator
(manual planning path and TiTO callback path) and the TiTO employee payload.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-01
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("is_minor", sa.Boolean(), server_default="0", nullable=False))
    op.add_column("employees", sa.Column("is_night_worker", sa.Boolean(), server_default="0", nullable=False))
    op.add_column("employees", sa.Column("night_worker_exam_date", sa.Date(), nullable=True))
    op.add_column("employees", sa.Column("protection_until", sa.Date(), nullable=True))
    op.add_column("employees", sa.Column("is_shift_worker", sa.Boolean(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("employees", "is_shift_worker")
    op.drop_column("employees", "protection_until")
    op.drop_column("employees", "night_worker_exam_date")
    op.drop_column("employees", "is_night_worker")
    op.drop_column("employees", "is_minor")
