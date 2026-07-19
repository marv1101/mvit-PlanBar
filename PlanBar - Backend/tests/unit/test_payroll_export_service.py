"""Unit tests for payroll export service (Issue #31)."""
import csv
import io
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.employee import Employee
from app.db.models.time_tracking import TimeEntry
from app.services.payroll_export_service import (
    calculate_overtime,
    determine_shift_type,
    generate_payroll_csv,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def employee(db_session):
    emp = Employee(first_name="Max", last_name="Mustermann")
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)
    return emp


def _make_entry(db, employee_id, clock_in, clock_out, duration_minutes, notes=None):
    entry = TimeEntry(
        employee_id=employee_id,
        clock_in=clock_in,
        clock_out=clock_out,
        duration_minutes=duration_minutes,
        notes=notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


class TestDetermineShiftType:
    def test_normal_daytime(self):
        dt = datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "normal"

    def test_normal_afternoon(self):
        dt = datetime(2026, 7, 13, 18, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "normal"

    def test_night_evening_boundary(self):
        dt = datetime(2026, 7, 13, 20, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "night"

    def test_night_late_evening(self):
        dt = datetime(2026, 7, 13, 22, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "night"

    def test_night_early_morning(self):
        dt = datetime(2026, 7, 13, 3, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "night"

    def test_night_before_6am(self):
        dt = datetime(2026, 7, 13, 5, 59, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "night"

    def test_normal_at_6am(self):
        dt = datetime(2026, 7, 13, 6, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "normal"

    def test_sunday(self):
        dt = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "sunday"

    def test_sunday_night(self):
        dt = datetime(2026, 7, 12, 22, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "sunday"

    def test_holiday_neujahr(self):
        dt = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_holiday_tag_der_arbeit(self):
        dt = datetime(2026, 5, 1, 14, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_holiday_christi_himmelfahrt(self):
        dt = datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_holiday_karfreitag(self):
        dt = datetime(2026, 4, 3, 8, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_holiday_ostermontag(self):
        dt = datetime(2026, 4, 6, 8, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_holiday_pfingstmontag(self):
        dt = datetime(2026, 5, 25, 8, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_holiday_fronleichnam(self):
        dt = datetime(2026, 6, 4, 8, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_holiday_tag_deutschen_einheit(self):
        dt = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_holiday_allerheiligen(self):
        dt = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_holiday_1_weihnachtstag(self):
        dt = datetime(2026, 12, 25, 10, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_holiday_2_weihnachtstag(self):
        dt = datetime(2026, 12, 26, 10, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_holiday_takes_precedence_over_sunday(self):
        dt = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "holiday"

    def test_non_holiday_friday(self):
        dt = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        assert determine_shift_type(dt) == "normal"


class TestCalculateOvertime:
    def test_no_entries(self, db_session, employee):
        result = calculate_overtime(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 12))
        assert result["total_scheduled_hours"] == 40.0
        assert result["total_actual_hours"] == 0.0
        assert result["total_overtime_hours"] == 0.0
        assert len(result["weeks"]) == 1

    def test_40h_week_no_overtime(self, db_session, employee):
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        for i in range(5):
            _make_entry(
                db_session, employee.id,
                clock_in=start + timedelta(days=i),
                clock_out=start + timedelta(days=i, hours=8),
                duration_minutes=480,
            )
        result = calculate_overtime(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 12))
        assert result["total_actual_hours"] == 40.0
        assert result["total_overtime_hours"] == 0.0

    def test_overtime_positive(self, db_session, employee):
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        for i in range(5):
            _make_entry(
                db_session, employee.id,
                clock_in=start + timedelta(days=i),
                clock_out=start + timedelta(days=i, hours=9),
                duration_minutes=540,
            )
        result = calculate_overtime(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 12))
        assert result["total_actual_hours"] == 45.0
        assert result["total_overtime_hours"] == 5.0
        assert result["weeks"][0]["overtime_hours"] == 5.0

    def test_multiple_weeks(self, db_session, employee):
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        for i in range(5):
            _make_entry(
                db_session, employee.id,
                clock_in=start + timedelta(days=i),
                clock_out=start + timedelta(days=i, hours=10),
                duration_minutes=600,
            )
        _make_entry(
            db_session, employee.id,
            clock_in=start + timedelta(days=7),
            clock_out=start + timedelta(days=7, hours=6),
            duration_minutes=360,
        )
        result = calculate_overtime(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 19))
        assert len(result["weeks"]) == 2
        assert result["weeks"][0]["overtime_hours"] == 10.0
        assert result["weeks"][1]["overtime_hours"] == 0.0

    def test_custom_weekly_hours(self, db_session, employee):
        employee.working_hours_json = '{"weekly_hours": 30}'
        db_session.commit()
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        for i in range(5):
            _make_entry(
                db_session, employee.id,
                clock_in=start + timedelta(days=i),
                clock_out=start + timedelta(days=i, hours=6),
                duration_minutes=360,
            )
        result = calculate_overtime(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 12))
        assert result["total_scheduled_hours"] == 30.0
        assert result["total_actual_hours"] == 30.0
        assert result["total_overtime_hours"] == 0.0


class TestGeneratePayrollCsv:
    def test_csv_has_utf8_bom(self, db_session, employee):
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        _make_entry(
            db_session, employee.id,
            clock_in=start,
            clock_out=start + timedelta(hours=8),
            duration_minutes=480,
        )
        csv_bytes = generate_payroll_csv(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 12))
        assert csv_bytes[:3] == b"\xef\xbb\xbf"

    def test_csv_column_order(self, db_session, employee):
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        _make_entry(
            db_session, employee.id,
            clock_in=start,
            clock_out=start + timedelta(hours=8),
            duration_minutes=480,
        )
        csv_bytes = generate_payroll_csv(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 12))
        csv_text = csv_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(csv_text))
        header = next(reader)
        assert header == [
            "Datum", "Kalenderwoche", "Wochentag", "Schichttyp",
            "Beginn", "Ende", "Dauer_Stunden", "Ueberstunden", "Notizen",
        ]

    def test_csv_duration_in_decimal_hours(self, db_session, employee):
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        _make_entry(
            db_session, employee.id,
            clock_in=start,
            clock_out=start + timedelta(hours=8, minutes=30),
            duration_minutes=510,
        )
        csv_bytes = generate_payroll_csv(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 12))
        csv_text = csv_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(csv_text))
        next(reader)  # skip header
        row = next(reader)
        assert row[6] == "8.50"

    def test_csv_overtime_only_in_summary(self, db_session, employee):
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        for i in range(5):
            _make_entry(
                db_session, employee.id,
                clock_in=start + timedelta(days=i),
                clock_out=start + timedelta(days=i, hours=9),
                duration_minutes=540,
            )
        csv_bytes = generate_payroll_csv(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 12))
        csv_text = csv_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(csv_text))
        next(reader)  # skip header
        # Daily rows should have empty overtime
        for _ in range(5):
            row = next(reader)
            assert row[7] == ""
        # Week summary row should have overtime
        summary = next(reader)
        assert summary[3] == "wochen_summe"
        assert summary[7] == "5.00"

    def test_csv_week_summary_row(self, db_session, employee):
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        _make_entry(
            db_session, employee.id,
            clock_in=start,
            clock_out=start + timedelta(hours=8),
            duration_minutes=480,
        )
        csv_bytes = generate_payroll_csv(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 12))
        csv_text = csv_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(csv_text))
        next(reader)  # header
        next(reader)  # daily row
        summary = next(reader)
        assert summary[3] == "wochen_summe"
        assert summary[6] == "8.00"

    def test_csv_total_summary_row(self, db_session, employee):
        start = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
        _make_entry(
            db_session, employee.id,
            clock_in=start,
            clock_out=start + timedelta(hours=8),
            duration_minutes=480,
        )
        csv_bytes = generate_payroll_csv(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 12))
        csv_text = csv_bytes.decode("utf-8-sig")
        lines = csv_text.strip().split("\n")
        total_line = lines[-1]
        reader = csv.reader(io.StringIO(total_line))
        total = next(reader)
        assert total[3] == "gesamt_summe"
        assert total[6] == "8.00"

    def test_csv_empty_entries(self, db_session, employee):
        csv_bytes = generate_payroll_csv(db_session, employee.id, date(2026, 7, 6), date(2026, 7, 12))
        csv_text = csv_bytes.decode("utf-8-sig")
        lines = csv_text.strip().split("\n")
        assert len(lines) == 3  # header + week summary + total summary
        reader = csv.reader(io.StringIO(lines[0]))
        header = next(reader)
        assert len(header) == 9

    def test_csv_shift_type_normal(self, db_session, employee):
        start = datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc)
        _make_entry(
            db_session, employee.id,
            clock_in=start,
            clock_out=start + timedelta(hours=8),
            duration_minutes=480,
        )
        csv_bytes = generate_payroll_csv(db_session, employee.id, date(2026, 7, 13), date(2026, 7, 19))
        csv_text = csv_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(csv_text))
        next(reader)  # header
        row = next(reader)
        assert row[3] == "normal"

    def test_csv_shift_type_night(self, db_session, employee):
        start = datetime(2026, 7, 13, 22, 0, tzinfo=timezone.utc)
        _make_entry(
            db_session, employee.id,
            clock_in=start,
            clock_out=start + timedelta(hours=8),
            duration_minutes=480,
        )
        csv_bytes = generate_payroll_csv(db_session, employee.id, date(2026, 7, 13), date(2026, 7, 19))
        csv_text = csv_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(csv_text))
        next(reader)  # header
        row = next(reader)
        assert row[3] == "night"

    def test_csv_shift_type_sunday(self, db_session, employee):
        start = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)
        _make_entry(
            db_session, employee.id,
            clock_in=start,
            clock_out=start + timedelta(hours=8),
            duration_minutes=480,
        )
        csv_bytes = generate_payroll_csv(db_session, employee.id, date(2026, 7, 12), date(2026, 7, 12))
        csv_text = csv_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(csv_text))
        next(reader)  # header
        row = next(reader)
        assert row[3] == "sunday"

    def test_csv_shift_type_holiday(self, db_session, employee):
        start = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
        _make_entry(
            db_session, employee.id,
            clock_in=start,
            clock_out=start + timedelta(hours=8),
            duration_minutes=480,
        )
        csv_bytes = generate_payroll_csv(db_session, employee.id, date(2026, 5, 1), date(2026, 5, 1))
        csv_text = csv_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(csv_text))
        next(reader)  # header
        row = next(reader)
        assert row[3] == "holiday"

    def test_invalid_date_range_raises(self, db_session, employee):
        with pytest.raises(ValueError, match="end_date must be >= start_date"):
            generate_payroll_csv(db_session, employee.id, date(2026, 7, 12), date(2026, 7, 6))

    def test_range_over_one_year_raises(self, db_session, employee):
        with pytest.raises(ValueError, match="Date range must not exceed"):
            generate_payroll_csv(db_session, employee.id, date(2026, 1, 1), date(2027, 1, 2))
