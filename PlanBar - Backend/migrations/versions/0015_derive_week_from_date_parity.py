"""derive shiftplans.week and shift_wishes.week from date parity

The week flag is now a derived, read-only value: week A/B is determined
by the calendar-week parity of the date (reference Monday 2024-01-01 = A).
This backfill resets any stored flags that contradict their date parity
and fills NULL values. Wishes use the numeric encoding 1 = A, 2 = B.

Dialect-agnostic (SQLite and PostgreSQL): parity is computed in Python
with the same math as app.services.schedule_service._get_week_type.

Revision ID: 0015
Revises: 0013, 0014
Create Date: 2026-08-30
"""

from datetime import date, timedelta

from alembic import op
from sqlalchemy import text

revision = "0015"
down_revision = ("0013", "0014")
branch_labels = None
depends_on = None


def _week_type(dt: date) -> str:
    monday = dt - timedelta(days=dt.weekday())
    reference = date(2024, 1, 1)
    weeks_diff = (monday - reference).days // 7
    return "A" if weeks_diff % 2 == 0 else "B"


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def upgrade() -> None:
    conn = op.get_bind()
    for table, week_a, week_b in (("shiftplans", "A", "B"), ("shift_wishes", 1, 2)):
        rows = conn.execute(text(f"SELECT id, date FROM {table}")).fetchall()
        for row_id, row_date in rows:
            value = week_a if _week_type(_as_date(row_date)) == "A" else week_b
            conn.execute(
                text(f"UPDATE {table} SET week = :week WHERE id = :id"),
                {"week": value, "id": row_id},
            )


def downgrade() -> None:
    pass
