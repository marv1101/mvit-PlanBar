"""Payroll export service (Issue #31 - Lohnabrechnungs-Export Phase 1)."""
import csv
import io
import json
from datetime import date, datetime, timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.employee import Employee
from app.db.models.time_tracking import TimeEntry

NRW_HOLIDAYS_2026 = {
    date(2026, 1, 1),    # Neujahr
    date(2026, 4, 3),    # Karfreitag
    date(2026, 4, 6),    # Ostermontag
    date(2026, 5, 1),    # Tag der Arbeit
    date(2026, 5, 14),   # Christi Himmelfahrt
    date(2026, 5, 25),   # Pfingstmontag
    date(2026, 6, 4),    # Fronleichnam
    date(2026, 10, 3),   # Tag der Deutschen Einheit
    date(2026, 11, 1),   # Allerheiligen
    date(2026, 12, 25),  # 1. Weihnachtstag
    date(2026, 12, 26),  # 2. Weihnachtstag
}

WEEKDAY_NAMES_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

CSV_HEADER = [
    "Datum", "Kalenderwoche", "Wochentag", "Schichttyp",
    "Beginn", "Ende", "Dauer_Stunden", "Ueberstunden", "Notizen",
]


def determine_shift_type(clock_in: datetime) -> str:
    d = clock_in.date()
    hour = clock_in.hour
    if d in NRW_HOLIDAYS_2026:
        return "holiday"
    if d.weekday() == 6:
        return "sunday"
    if hour >= 20 or hour < 6:
        return "night"
    return "normal"


def _get_employee(db: Session, employee_id: int) -> Employee:
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise ValueError(f"Employee not found: {employee_id}")
    return emp


def _get_weekly_hours(employee: Employee) -> float:
    if employee.working_hours_json:
        try:
            data = json.loads(employee.working_hours_json)
            if "weekly_hours" in data:
                return float(data["weekly_hours"])
        except (json.JSONDecodeError, TypeError):
            pass
    return 40.0


def _get_entries_in_range(
    db: Session, employee_id: int, start_date: date, end_date: date
) -> List[TimeEntry]:
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    stmt = (
        select(TimeEntry)
        .where(TimeEntry.employee_id == employee_id)
        .where(TimeEntry.clock_in >= start_dt)
        .where(TimeEntry.clock_in < end_dt)
        .order_by(TimeEntry.clock_in.asc())
    )
    return list(db.execute(stmt).scalars().all())


def _iso_week_label(d: date) -> tuple[int, int]:
    kw = d.isocalendar()
    return kw[1], kw[0]


def _week_key(d: date) -> tuple[int, int]:
    iso = d.isocalendar()
    return iso[1], iso[0]


def calculate_overtime(
    db: Session, employee_id: int, start_date: date, end_date: date
) -> dict:
    employee = _get_employee(db, employee_id)
    weekly_hours = _get_weekly_hours(employee)
    entries = _get_entries_in_range(db, employee_id, start_date, end_date)

    week_map: dict[tuple[int, int], float] = {}
    for entry in entries:
        wk = _week_key(entry.clock_in.date())
        mins = entry.duration_minutes or 0
        week_map[wk] = week_map.get(wk, 0.0) + mins / 60.0

    weeks = []
    total_actual = 0.0
    total_scheduled = 0.0
    cur = start_date
    seen_weeks = set()
    while cur <= end_date:
        wk = _week_key(cur)
        if wk not in seen_weeks:
            seen_weeks.add(wk)
            actual = week_map.get(wk, 0.0)
            overtime = max(0.0, actual - weekly_hours)
            weeks.append({
                "year": wk[1],
                "week": wk[0],
                "scheduled_hours": weekly_hours,
                "actual_hours": round(actual, 2),
                "overtime_hours": round(overtime, 2),
            })
            total_actual += actual
            total_scheduled += weekly_hours
        cur += timedelta(days=1)

    return {
        "employee_id": employee_id,
        "start_date": start_date,
        "end_date": end_date,
        "total_scheduled_hours": round(total_scheduled, 2),
        "total_actual_hours": round(total_actual, 2),
        "total_overtime_hours": round(max(0.0, total_actual - total_scheduled), 2),
        "weeks": weeks,
    }


def generate_payroll_csv(
    db: Session, employee_id: int, start_date: date, end_date: date
) -> bytes:
    if end_date < start_date:
        raise ValueError("end_date must be >= start_date")
    if (end_date - start_date).days > 365:
        raise ValueError("Date range must not exceed 1 year")

    _get_employee(db, employee_id)
    entries = _get_entries_in_range(db, employee_id, start_date, end_date)
    overtime = calculate_overtime(db, employee_id, start_date, end_date)

    overtime_by_week: dict[tuple[int, int], float] = {}
    for w in overtime["weeks"]:
        overtime_by_week[(w["week"], w["year"])] = w["overtime_hours"]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_HEADER)

    seen_weeks: dict[tuple[int, int], float] = {}

    for entry in entries:
        d = entry.clock_in.date()
        wk = _week_key(d)
        kw, jahr = _iso_week_label(d)
        weekday_de = WEEKDAY_NAMES_DE[d.weekday()]
        shift_type = determine_shift_type(entry.clock_in)
        beginn = entry.clock_in.strftime("%H:%M")
        ende = entry.clock_out.strftime("%H:%M") if entry.clock_out else ""
        duration_hours = round((entry.duration_minutes or 0) / 60.0, 2)

        seen_weeks[wk] = seen_weeks.get(wk, 0.0) + duration_hours

        writer.writerow([
            d.isoformat(),
            f"{jahr}-KW{kw:02d}",
            weekday_de,
            shift_type,
            beginn,
            ende,
            f"{duration_hours:.2f}",
            "",
            entry.notes or "",
        ])

    cur = start_date
    written_weeks = set()
    total_duration = 0.0
    while cur <= end_date:
        wk = _week_key(cur)
        if wk not in written_weeks and wk in seen_weeks:
            written_weeks.add(wk)
            kw, jahr = _iso_week_label(cur)
            week_dur = seen_weeks[wk]
            week_ot = overtime_by_week.get(wk, 0.0)
            total_duration += week_dur
            writer.writerow([
                f"{jahr}-KW{kw:02d}",
                f"{jahr}-KW{kw:02d}",
                "",
                "wochen_summe",
                "",
                "",
                f"{week_dur:.2f}",
                f"{week_ot:.2f}",
                "",
            ])
        cur += timedelta(days=1)

    if not seen_weeks:
        cur = start_date
        while cur <= end_date:
            wk = _week_key(cur)
            if wk not in written_weeks:
                written_weeks.add(wk)
                kw, jahr = _iso_week_label(cur)
                writer.writerow([
                    f"{jahr}-KW{kw:02d}",
                    f"{jahr}-KW{kw:02d}",
                    "",
                    "wochen_summe",
                    "",
                    "",
                    "0.00",
                    "0.00",
                    "",
                ])
            cur += timedelta(days=1)
        total_duration = 0.0

    writer.writerow([
        "",
        "",
        "",
        "gesamt_summe",
        "",
        "",
        f"{round(total_duration, 2):.2f}",
        f"{overtime['total_overtime_hours']:.2f}",
        "",
    ])

    csv_text = buf.getvalue()
    return ("\ufeff" + csv_text).encode("utf-8")
