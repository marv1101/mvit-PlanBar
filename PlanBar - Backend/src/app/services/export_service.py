"""Export service for schedule PDF and iCal generation."""

import io
from datetime import UTC, datetime

from icalendar import Calendar, Event
from sqlalchemy.orm import Session

from app.db.models.employee import Employee
from app.db.models.schedule import Schedule, Shiftplan


def _get_schedule_with_shifts(db: Session, schedule_id: int) -> tuple[Schedule | None, list[Shiftplan]]:
    """Load a schedule and its shifts, returning (schedule, shifts) or (None, [])."""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        return None, []
    shifts = (
        db.query(Shiftplan)
        .filter(Shiftplan.schedule_id == schedule_id)
        .order_by(Shiftplan.date, Shiftplan.start_time)
        .all()
    )
    return schedule, shifts


def _employee_name(db: Session, employee_id: int) -> str:
    """Look up employee full name."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if emp:
        return f"{emp.first_name} {emp.last_name}"
    return f"Employee #{employee_id}"


def _safe_text(text: str) -> str:
    """Strip characters unsupported by fpdf2 core fonts (latin-1)."""
    replacements = {
        "\u2013": "-",  # en-dash
        "\u2014": "-",  # em-dash
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2022": "*",  # bullet
        "\u00fc": "ue",  # u-umlaut
        "\u00e4": "ae",  # a-umlaut
        "\u00f6": "oe",  # o-umlaut
        "\u00dc": "Ue",  # U-umlaut
        "\u00c4": "Ae",  # A-umlaut
        "\u00d6": "Oe",  # O-umlaut
        "\u00df": "ss",  # sharp s
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Final fallback: encode to latin-1, replacing anything else
    return text.encode("latin-1", errors="replace").decode("latin-1")


def export_schedule_ical(db: Session, schedule_id: int) -> bytes | None:
    """Generate an iCal file for the given schedule.

    Returns iCal bytes or None if schedule not found.
    """
    schedule, shifts = _get_schedule_with_shifts(db, schedule_id)
    if not schedule:
        return None

    cal = Calendar()
    cal.add("prodid", "-//PlanBar//Schedule Export//DE")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", schedule.name)

    for shift in shifts:
        emp_name = _employee_name(db, shift.employee_id)

        # Build event datetime (date + time)
        start_dt = datetime.combine(shift.date, shift.start_time, tzinfo=UTC)
        # Handle overnight shifts: if end_time <= start_time, assume next day
        if shift.end_time <= shift.start_time:
            from datetime import timedelta

            end_date = shift.date + timedelta(days=1)
        else:
            end_date = shift.date
        end_dt = datetime.combine(end_date, shift.end_time, tzinfo=UTC)

        event = Event()
        event.add("summary", f"{shift.label or shift.shift_id} - {emp_name}")
        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)
        event.add("description", f"Schicht: {shift.shift_id}\nMitarbeiter: {emp_name}")
        if shift.notes:
            event.add("description", f"{event.get('description')}\nNotizen: {shift.notes}")
        event.add("uid", f"planbar-shift-{shift.id}@planbar")
        cal.add_component(event)

    return cal.to_ical()


def export_schedule_pdf(db: Session, schedule_id: int) -> bytes | None:
    """Generate a PDF file for the given schedule.

    Returns PDF bytes or None if schedule not found.
    """
    from fpdf import FPDF

    schedule, shifts = _get_schedule_with_shifts(db, schedule_id)
    if not schedule:
        return None

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Title page ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 15, _safe_text(schedule.name), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 12)
    if schedule.start_date and schedule.end_date:
        date_range = f"{schedule.start_date.strftime('%d.%m.%Y')} - {schedule.end_date.strftime('%d.%m.%Y')}"
        pdf.cell(0, 8, date_range, new_x="LMARGIN", new_y="NEXT", align="C")
    if schedule.week_type:
        pdf.cell(0, 8, f"Wochentyp: {schedule.week_type}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)

    # Summary
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Zusammenfassung", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Status: {schedule.status}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Anzahl Schichten: {len(shifts)}", new_x="LMARGIN", new_y="NEXT")
    employee_ids = {s.employee_id for s in shifts}
    pdf.cell(0, 7, f"Mitarbeiter: {len(employee_ids)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # --- Shifts table ---
    if shifts:
        pdf.add_page("L")
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Schichtdetails", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

        # Table header
        col_widths = [25, 55, 65, 30, 30, 30, 30, 50]
        headers = ["Datum", "Mitarbeiter", "Schicht", "Start", "Ende", "Pause V.", "Pause E.", "Notizen"]
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 230, 241)
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, _safe_text(header), border=1, fill=True, align="C")
        pdf.ln()

        # Table rows
        pdf.set_font("Helvetica", "", 8)
        for shift in shifts:
            emp_name = _employee_name(db, shift.employee_id)
            row = [
                shift.date.strftime("%d.%m.%Y") if shift.date else "",
                emp_name,
                _safe_text(shift.label or shift.shift_id),
                shift.start_time.strftime("%H:%M") if shift.start_time else "",
                shift.end_time.strftime("%H:%M") if shift.end_time else "",
                shift.break_start or "",
                shift.break_end or "",
                _safe_text((shift.notes or "")[:30]),
            ]
            for i, val in enumerate(row):
                pdf.cell(col_widths[i], 6, val, border=1, align="C")
            pdf.ln()

    # --- Footer ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(
        0,
        5,
        f"Exportiert am {datetime.now(UTC).strftime('%d.%m.%Y %H:%M')}",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )

    # Write to bytes buffer
    buf = io.BytesIO()
    pdf_bytes = pdf.output()
    buf.write(pdf_bytes)
    return buf.getvalue()
