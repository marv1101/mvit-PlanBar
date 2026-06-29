import io
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from fpdf import FPDF
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models.employee import Employee, Timecard
from app.db.models.schedule import Shiftplan
from app.services.export_service import _safe_text


def _date_range_to_weeks(start: date, end: date) -> set[tuple[int, int]]:
    weeks = set()
    current = start
    while current <= end:
        iso = current.isocalendar()
        weeks.add((iso[0], iso[1]))
        current += timedelta(days=1)
    return weeks


def _shift_duration_hours(shift: Shiftplan) -> float:
    start_dt = datetime.combine(shift.date, shift.start_time)
    end_dt = datetime.combine(shift.date, shift.end_time)
    if shift.end_time <= shift.start_time:
        end_dt += timedelta(days=1)
    return round((end_dt - start_dt).total_seconds() / 3600, 2)


def _parse_break_minutes(break_str: str) -> int:
    parts = break_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def generate_overtime_report(
    db: Session,
    employee_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(weeks=4)

    query = db.query(Timecard)

    if employee_id:
        query = query.filter(Timecard.employee_id == employee_id)

    weeks = _date_range_to_weeks(start_date, end_date)
    week_filters = [(Timecard.year == y) & (Timecard.week == w) for y, w in weeks]
    query = query.filter(or_(*week_filters))

    timecards = query.all()

    emp_data: dict[int, dict] = {}
    for tc in timecards:
        if tc.employee_id not in emp_data:
            emp_data[tc.employee_id] = {"scheduled": 0.0, "actual": 0.0, "contract": 0.0}
        emp_data[tc.employee_id]["scheduled"] += tc.scheduled_hours or 0
        emp_data[tc.employee_id]["actual"] += tc.actual_hours or 0
        emp_data[tc.employee_id]["contract"] += tc.contract_hours or 0

    employees = []
    for emp_id, data in emp_data.items():
        emp = db.query(Employee).filter(Employee.id == emp_id).first()
        name = f"{emp.first_name} {emp.last_name}" if emp else f"Employee #{emp_id}"
        overtime = data["actual"] - data["contract"]
        employees.append({
            "employee_id": emp_id,
            "employee_name": name,
            "total_scheduled_hours": round(data["scheduled"], 2),
            "total_actual_hours": round(data["actual"], 2),
            "total_contract_hours": round(data["contract"], 2),
            "overtime_hours": round(overtime, 2),
        })

    return {
        "employees": employees,
        "summary": {
            "total_employees": len(employees),
            "total_overtime_hours": round(sum(e["overtime_hours"] for e in employees), 2),
            "start_date": str(start_date),
            "end_date": str(end_date),
        },
    }


def generate_compliance_report(
    db: Session,
    employee_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(weeks=4)

    query = db.query(Shiftplan).filter(
        Shiftplan.date >= start_date,
        Shiftplan.date <= end_date,
    )
    if employee_id:
        query = query.filter(Shiftplan.employee_id == employee_id)

    shifts = query.order_by(Shiftplan.employee_id, Shiftplan.date, Shiftplan.start_time).all()

    violations = []
    total_employees_checked: set[int] = set()
    total_shifts_checked = len(shifts)

    emp_shifts: dict[int, list[Shiftplan]] = defaultdict(list)
    for s in shifts:
        emp_shifts[s.employee_id].append(s)
        total_employees_checked.add(s.employee_id)

    for emp_id, emp_shift_list in emp_shifts.items():
        sorted_shifts = sorted(emp_shift_list, key=lambda s: (s.date, s.start_time))
        emp = db.query(Employee).filter(Employee.id == emp_id).first()
        emp_name = f"{emp.first_name} {emp.last_name}" if emp else f"Employee #{emp_id}"

        for i in range(len(sorted_shifts) - 1):
            current = sorted_shifts[i]
            next_s = sorted_shifts[i + 1]

            current_end = datetime.combine(current.date, current.end_time)
            if current.end_time <= current.start_time:
                current_end += timedelta(days=1)

            next_start = datetime.combine(next_s.date, next_s.start_time)
            rest_hours = (next_start - current_end).total_seconds() / 3600

            if rest_hours < 11:
                violations.append({
                    "rule": "rest_period",
                    "message": (
                        f"Nur {rest_hours:.1f}h Ruhezeit zwischen Schichten "
                        f"am {current.date} und {next_s.date} (benoetigt: 11h)"
                    ),
                    "employee_id": emp_id,
                    "employee_name": emp_name,
                    "shift_date": str(current.date),
                    "severity": "error",
                    "details": {
                        "previous_shift_end": current.end_time.strftime("%H:%M"),
                        "next_shift_start": next_s.start_time.strftime("%H:%M"),
                        "actual_rest_hours": round(rest_hours, 1),
                        "required_rest_hours": 11.0,
                    },
                })

    for shift in shifts:
        emp = db.query(Employee).filter(Employee.id == shift.employee_id).first()
        emp_name = f"{emp.first_name} {emp.last_name}" if emp else f"Employee #{shift.employee_id}"
        hours = _shift_duration_hours(shift)

        if hours > 10:
            violations.append({
                "rule": "max_hours",
                "message": (
                    f"Arbeitszeit von {hours:.1f}h am {shift.date} "
                    f"ueberschreitet 10h Grenze (Paragraph 3 ArbZG)"
                ),
                "employee_id": shift.employee_id,
                "employee_name": emp_name,
                "shift_date": str(shift.date),
                "severity": "error",
                "details": {
                    "actual_hours": round(hours, 1),
                    "max_allowed": 10.0,
                    "start_time": shift.start_time.strftime("%H:%M"),
                    "end_time": shift.end_time.strftime("%H:%M"),
                },
            })
        elif hours > 8:
            violations.append({
                "rule": "max_hours_warning",
                "message": (
                    f"Arbeitszeit von {hours:.1f}h am {shift.date} "
                    f"ueberschreitet 8h (Paragraph 3 ArbZG), "
                    f"Ausgleich innerhalb 6 Monaten erforderlich"
                ),
                "employee_id": shift.employee_id,
                "employee_name": emp_name,
                "shift_date": str(shift.date),
                "severity": "warning",
                "details": {
                    "actual_hours": round(hours, 1),
                    "max_allowed_without_compensation": 8.0,
                    "start_time": shift.start_time.strftime("%H:%M"),
                    "end_time": shift.end_time.strftime("%H:%M"),
                },
            })

    for shift in shifts:
        hours = _shift_duration_hours(shift)
        if hours <= 6:
            continue

        emp = db.query(Employee).filter(Employee.id == shift.employee_id).first()
        emp_name = f"{emp.first_name} {emp.last_name}" if emp else f"Employee #{shift.employee_id}"

        if not shift.break_start or not shift.break_end:
            violations.append({
                "rule": "break_missing",
                "message": (
                    f"Keine Pause bei {hours:.1f}h Arbeitszeit "
                    f"am {shift.date} (Paragraph 4 ArbZG)"
                ),
                "employee_id": shift.employee_id,
                "employee_name": emp_name,
                "shift_date": str(shift.date),
                "severity": "error",
                "details": {
                    "actual_hours": round(hours, 1),
                    "required_break_minutes": 45 if hours > 9 else 30,
                },
            })
        else:
            b_start = datetime.strptime(shift.break_start, "%H:%M")
            b_end = datetime.strptime(shift.break_end, "%H:%M")
            break_minutes = (b_end - b_start).total_seconds() / 60
            required = 45 if hours > 9 else 30

            if break_minutes < required:
                violations.append({
                    "rule": "break_too_short",
                    "message": (
                        f"Pause von nur {int(break_minutes)}min bei {hours:.1f}h "
                        f"Arbeitszeit am {shift.date} (Paragraph 4 ArbZG)"
                    ),
                    "employee_id": shift.employee_id,
                    "employee_name": emp_name,
                    "shift_date": str(shift.date),
                    "severity": "error",
                    "details": {
                        "actual_break_minutes": int(break_minutes),
                        "required_break_minutes": required,
                    },
                })

    return {
        "violations": violations,
        "summary": {
            "total_violations": len(violations),
            "rest_period_violations": sum(1 for v in violations if v["rule"] == "rest_period"),
            "max_hours_violations": sum(1 for v in violations if v["rule"].startswith("max_hours")),
            "break_violations": sum(1 for v in violations if v["rule"].startswith("break")),
            "checked_employees": len(total_employees_checked),
            "checked_shifts": total_shifts_checked,
            "start_date": str(start_date),
            "end_date": str(end_date),
        },
    }


def export_overtime_pdf(report_data: dict) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, _safe_text("Ueberstunden-Report"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    summary = report_data["summary"]
    pdf.cell(
        0, 6,
        f"Zeitraum: {summary['start_date']} - {summary['end_date']}",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(
        0, 8,
        f"Gesamt: {summary['total_overtime_hours']} Ueberstunden bei {summary['total_employees']} Mitarbeitern",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(5)

    col_widths = [10, 50, 35, 35, 35, 35]
    headers = ["ID", "Mitarbeiter", "Geplant", "Ist", "Soll", "Ueberstd."]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 230, 241)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for emp in report_data["employees"]:
        row = [
            str(emp["employee_id"]),
            _safe_text(emp["employee_name"]),
            str(emp["total_scheduled_hours"]),
            str(emp["total_actual_hours"]),
            str(emp["total_contract_hours"]),
            str(emp["overtime_hours"]),
        ]
        for i, val in enumerate(row):
            pdf.cell(col_widths[i], 6, val, border=1, align="C")
        pdf.ln()

    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(
        0, 5,
        f"Generiert am {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )

    buf = io.BytesIO()
    buf.write(pdf.output())
    return buf.getvalue()


def export_compliance_pdf(report_data: dict) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 15, _safe_text("ArbZG-Compliance-Report"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    summary = report_data["summary"]
    pdf.cell(
        0, 6,
        f"Zeitraum: {summary['start_date']} - {summary['end_date']}",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(
        0, 8,
        f"Verstoesse: {summary['total_violations']} (Geprueft: {summary['checked_employees']} Mitarbeiter, {summary['checked_shifts']} Schichten)",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(5)

    col_widths = [8, 40, 20, 18, 90]
    headers = ["#", "Mitarbeiter", "Regel", "Status", "Nachricht"]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 230, 241)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for idx, v in enumerate(report_data["violations"], 1):
        severity_label = "FEHLER" if v["severity"] == "error" else "WARNUNG"
        row = [
            str(idx),
            _safe_text(v["employee_name"][:20]),
            _safe_text(v["rule"][:18]),
            severity_label,
            _safe_text(v["message"][:60]),
        ]
        for i, val in enumerate(row):
            pdf.cell(col_widths[i], 6, val, border=1, align="C")
        pdf.ln()

    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(
        0, 5,
        f"Generiert am {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )

    buf = io.BytesIO()
    buf.write(pdf.output())
    return buf.getvalue()
