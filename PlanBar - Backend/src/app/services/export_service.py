"""Export service for schedule PDF and iCal generation."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fpdf import FPDF
from icalendar import Calendar, Event
from sqlalchemy.orm import Session

from app.db.models.employee import Employee
from app.db.models.schedule import Schedule, Shiftplan

_DAY_ABBR = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
_DAY_FULL = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]
_FALLBACK_COLOR = (203, 203, 203)


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
    """Replace typographic characters unsupported by fpdf2 core fonts (latin-1).

    Umlauts (ä/ö/ü/ß and uppercase variants) are latin-1 safe and are kept
    intact so that names like "Müller" are not corrupted to "Mueller". Any
    remaining non-latin-1 character is replaced via the latin-1 fallback.
    """
    replacements = {
        "\u2013": "-",  # en-dash
        "\u2014": "-",  # em-dash
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2022": "*",  # bullet
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
        start_dt = datetime.combine(shift.date, shift.start_time, tzinfo=timezone.utc)
        # Handle overnight shifts: if end_time <= start_time, assume next day
        if shift.end_time <= shift.start_time:
            from datetime import timedelta

            end_date = shift.date + timedelta(days=1)
        else:
            end_date = shift.date
        end_dt = datetime.combine(end_date, shift.end_time, tzinfo=timezone.utc)

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


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_str: str | None) -> tuple[int, int, int]:
    """Convert a '#rrggbb' hex string to an (r, g, b) tuple.

    Returns a neutral gray fallback for missing or invalid values.
    """
    if not hex_str:
        return _FALLBACK_COLOR
    value = hex_str.strip()
    if len(value) != 7 or value[0] != "#":
        return _FALLBACK_COLOR
    try:
        return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))
    except ValueError:
        return _FALLBACK_COLOR


def _lighten(rgb: tuple[int, int, int], factor: float = 0.85) -> tuple[int, int, int]:
    """Blend an RGB color towards white by the given factor (0..1)."""
    r, g, b = rgb
    return (
        int(r + (255 - r) * factor),
        int(g + (255 - g) * factor),
        int(b + (255 - b) * factor),
    )


def _week_parity(d: date) -> str:
    """Return the 'A'/'B' week type for a date, mirroring the frontend logic.

    Weeks since the Monday of 2024-01-01; even -> 'A', odd -> 'B'.
    """
    monday = d - timedelta(days=d.weekday())
    weeks = (monday - date(2024, 1, 1)).days // 7
    return "A" if weeks % 2 == 0 else "B"


def _employee_info(db: Session, employee_ids: set[int]) -> dict[int, Employee]:
    """Load multiple employees in a single query (avoids N+1 lookups)."""
    if not employee_ids:
        return {}
    employees = db.query(Employee).filter(Employee.id.in_(employee_ids)).all()
    return {emp.id: emp for emp in employees}


def _schedule_range(schedule: Schedule, shifts: list[Shiftplan]) -> tuple[date, date] | None:
    """Determine the date range covered by the PDF (schedule dates or shift dates)."""
    if schedule.start_date and schedule.end_date:
        return schedule.start_date, schedule.end_date
    if not shifts:
        return None
    dates = [s.date for s in shifts]
    return min(dates), max(dates)


def _build_week_buckets(
    start: date, end: date, shifts: list[Shiftplan]
) -> list[dict]:
    """Group the [start..end] range into weekly buckets keyed by their Monday.

    Each bucket carries its parity ('A'/'B') and a dict of date -> shifts for
    the full Monday..Sunday week (days outside the schedule range map to an
    empty list and are shaded differently when rendered).
    """
    shifts_by_day: dict[date, list[Shiftplan]] = {}
    for shift in shifts:
        shifts_by_day.setdefault(shift.date, []).append(shift)
    for day_shifts in shifts_by_day.values():
        day_shifts.sort(key=lambda sh: sh.start_time)

    partial: dict[date, dict] = {}
    current = start
    while current <= end:
        monday = current - timedelta(days=current.weekday())
        parity = _week_parity(current)
        bucket = partial.setdefault(
            monday, {"monday": monday, "parity": parity, "days": {}}
        )
        bucket["days"][current] = shifts_by_day.get(current, [])
        current += timedelta(days=1)

    buckets: list[dict] = []
    for monday in sorted(partial):
        bucket = partial[monday]
        full_days: dict[date, list[Shiftplan]] = {}
        for offset in range(7):
            day = monday + timedelta(days=offset)
            full_days[day] = bucket["days"].get(day, [])
        buckets.append(
            {"monday": monday, "parity": bucket["parity"], "days": full_days}
        )
    return buckets


class _SchedulePdf(FPDF):
    """FPDF subclass rendering a schedule header and a Berlin-time footer."""

    def __init__(self, schedule_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._schedule_name = schedule_name

    def header(self) -> None:
        """Render the page header (skipped on the cover page)."""
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 9)
        self.cell(
            0,
            6,
            _safe_text(self._schedule_name),
            align="L",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    def footer(self) -> None:
        """Render the export timestamp (Europe/Berlin) and the page number."""
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        stamp = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y %H:%M")
        self.cell(
            0,
            5,
            f"Exportiert am {stamp} Uhr",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.cell(0, 5, f"Seite {self.page_no()}", align="R")


def _render_cover_page(
    pdf: _SchedulePdf,
    schedule: Schedule,
    shifts: list[Shiftplan],
    employee_info: dict[int, Employee],
) -> None:
    """Render the cover page: title, date range, summary and legend."""
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(
        0,
        12,
        _safe_text(schedule.name),
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 12)
    if schedule.start_date and schedule.end_date:
        date_range = (
            f"{schedule.start_date.strftime('%d.%m.%Y')} - "
            f"{schedule.end_date.strftime('%d.%m.%Y')}"
        )
        pdf.cell(0, 8, _safe_text(date_range), align="C", new_x="LMARGIN", new_y="NEXT")
    if schedule.week_type:
        pdf.cell(
            0,
            8,
            _safe_text(
                f"Wochentyp: {schedule.week_type} (nur {schedule.week_type}-Wochen)"
            ),
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Zusammenfassung", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, _safe_text(f"Status: {schedule.status}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Anzahl Schichten: {len(shifts)}", new_x="LMARGIN", new_y="NEXT")
    employee_ids = {s.employee_id for s in shifts}
    pdf.cell(
        0,
        6,
        f"Anzahl Mitarbeiter: {len(employee_ids)}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Legende", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    employees = [
        employee_info[eid] for eid in employee_ids if employee_info.get(eid) is not None
    ]
    employees.sort(key=lambda emp: f"{emp.first_name} {emp.last_name}")
    for emp in employees:
        x = pdf.get_x()
        y = pdf.get_y()
        pdf.set_fill_color(*_hex_to_rgb(emp.color))
        pdf.rect(x, y, 5, 5, style="F")
        pdf.set_xy(x + 7, y)
        pdf.cell(
            0,
            5,
            _safe_text(f"{emp.first_name} {emp.last_name}"),
            align="L",
            new_x="LMARGIN",
            new_y="NEXT",
        )


def _render_shift_chip(
    pdf: _SchedulePdf,
    shift: Shiftplan,
    employee_info: dict[int, Employee],
    col_x: float,
    y: float,
    col_w: float,
) -> None:
    """Render a single shift chip inside a calendar day cell."""
    emp = employee_info.get(shift.employee_id)
    color = _hex_to_rgb(emp.color if emp else None)
    light = _lighten(color)
    chip_w = col_w - 3
    chip_x = col_x + 1.5
    chip_h = 12.0

    pdf.set_fill_color(*light)
    pdf.rect(chip_x, y, chip_w, chip_h, style="F")
    pdf.set_fill_color(*color)
    pdf.rect(chip_x, y, 1.5, chip_h, style="F")

    text_x = chip_x + 2.5
    text_w = chip_w - 1.5
    pdf.set_xy(text_x, y + 0.5)
    pdf.set_font("Helvetica", "B", 7)
    first_name = emp.first_name if emp else f"Employee #{shift.employee_id}"
    pdf.cell(text_w, 2.5, _safe_text(first_name), align="L")

    start_str = shift.start_time.strftime("%H:%M")
    end_str = shift.end_time.strftime("%H:%M")
    pdf.set_xy(text_x, y + 3)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(text_w, 2.5, f"{start_str} - {end_str}", align="L")

    if shift.break_start and shift.break_end:
        pdf.set_xy(text_x, y + 5.5)
        pdf.set_font("Helvetica", "", 6)
        pdf.cell(text_w, 2.5, f"Pause {shift.break_start} - {shift.break_end}", align="L")

    if shift.label:
        pdf.set_xy(text_x, y + 8)
        pdf.set_font("Helvetica", "I", 6)
        pdf.cell(text_w, 2.5, _safe_text(shift.label), align="L")


def _render_calendar_page(
    pdf: _SchedulePdf,
    bucket: dict,
    employee_info: dict[int, Employee],
    range_start: date,
    range_end: date,
) -> None:
    """Render a single calendar week page (7-column day grid)."""
    monday: date = bucket["monday"]
    parity: str = bucket["parity"]
    days: dict[date, list[Shiftplan]] = bucket["days"]
    sunday = monday + timedelta(days=6)
    iso_week = monday.isocalendar()[1]

    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(200, 200, 200)

    pdf.set_font("Helvetica", "B", 14)
    title = (
        f"Kalender Woche {parity} (KW {iso_week}: "
        f"{monday.strftime('%d.%m.')} - {sunday.strftime('%d.%m.%Y')})"
    )
    pdf.cell(0, 8, _safe_text(title), new_x="LMARGIN", new_y="NEXT")

    col_w = pdf.epw / 7
    pdf.set_font("Helvetica", "B", 9)
    for name in _DAY_FULL:
        pdf.cell(col_w, 6, name, border=1, align="C")
    pdf.ln()

    grid_top = pdf.get_y()
    grid_bottom = pdf.h - 14  # keep clear of the footer
    cell_h = grid_bottom - grid_top
    margin = pdf.l_margin

    for offset in range(7):
        day = monday + timedelta(days=offset)
        x = margin + offset * col_w
        in_range = range_start <= day <= range_end
        is_weekend = day.weekday() >= 5
        if not in_range:
            bg = (235, 235, 235)
        elif is_weekend:
            bg = (245, 245, 245)
        else:
            bg = (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.rect(x, grid_top, col_w, cell_h, style="FD")

        if not in_range:
            continue

        pdf.set_xy(x + 1, grid_top + 1)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_w - 2, 4, f"{_DAY_ABBR[offset]}, {day.strftime('%d.%m.')}", align="L")

        day_shifts = days.get(day, [])
        if day_shifts:
            chip_y = grid_top + 6
            for shift in day_shifts:
                if chip_y + 13 > grid_bottom:
                    break
                _render_shift_chip(pdf, shift, employee_info, x, chip_y, col_w)
                chip_y += 13
        else:
            pdf.set_xy(x + 1, grid_top + 6)
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(128, 128, 128)
            pdf.cell(col_w - 2, 5, "Keine Schichten", align="L")
            pdf.set_text_color(0, 0, 0)


def _render_calendar_pages(
    pdf: _SchedulePdf,
    schedule: Schedule,
    shifts: list[Shiftplan],
    employee_info: dict[int, Employee],
) -> None:
    """Render one calendar page per week bucket (A/B weeks separated)."""
    if not shifts:
        return
    date_range = _schedule_range(schedule, shifts)
    if date_range is None:
        return
    start, end = date_range
    buckets = _build_week_buckets(start, end, shifts)
    if schedule.week_type in ("A", "B"):
        buckets = [b for b in buckets if b["parity"] == schedule.week_type]
    if not buckets:
        return

    pdf.set_auto_page_break(False)
    for bucket in buckets:
        _render_calendar_page(pdf, bucket, employee_info, start, end)
    pdf.set_auto_page_break(True, margin=15)


def _render_list_row(
    pdf: _SchedulePdf,
    shift: Shiftplan,
    employee_info: dict[int, Employee],
    widths: list[float],
) -> None:
    """Render a single shift row in the list table (with a color bar)."""
    emp = employee_info.get(shift.employee_id)
    color = _hex_to_rgb(emp.color if emp else None)
    name = (
        f"{emp.first_name} {emp.last_name}"
        if emp
        else f"Employee #{shift.employee_id}"
    )
    label = shift.label or shift.shift_id
    start_str = shift.start_time.strftime("%H:%M")
    end_str = shift.end_time.strftime("%H:%M")
    pause = (
        f"{shift.break_start} - {shift.break_end}"
        if (shift.break_start and shift.break_end)
        else ""
    )
    notes = _safe_text((shift.notes or "")[:40])
    row_h = 6.0

    x0 = pdf.get_x()
    y0 = pdf.get_y()
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(widths[0], row_h, " " + _safe_text(name), border=1, align="L")
    pdf.set_fill_color(*color)
    pdf.rect(x0, y0, 1.5, row_h, style="F")
    pdf.cell(widths[1], row_h, _safe_text(label), border=1, align="C")
    pdf.cell(widths[2], row_h, start_str, border=1, align="C")
    pdf.cell(widths[3], row_h, end_str, border=1, align="C")
    pdf.cell(widths[4], row_h, pause, border=1, align="C")
    pdf.cell(widths[5], row_h, notes, border=1, align="C")


def _render_list_pages(
    pdf: _SchedulePdf,
    shifts: list[Shiftplan],
    employee_info: dict[int, Employee],
) -> None:
    """Render the chronological shift list (grouped by day)."""
    if not shifts:
        return
    widths = [60.0, 65.0, 30.0, 30.0, 45.0, 47.0]
    headers = ["Mitarbeiter", "Schicht", "Start", "Ende", "Pause", "Notizen"]

    def _table_header() -> None:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(220, 230, 241)
        for width, header in zip(widths, headers):
            pdf.cell(width, 6, header, border=1, fill=True, align="C")
        pdf.ln()

    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Schichtliste", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    days = sorted({shift.date for shift in shifts})
    shifts_by_day: dict[date, list[Shiftplan]] = {
        day: sorted([s for s in shifts if s.date == day], key=lambda s: s.start_time)
        for day in days
    }

    for day in days:
        day_shifts = shifts_by_day[day]
        block_h = 6 + 6 + 6 * len(day_shifts)
        if pdf.will_page_break(block_h):
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(
            0,
            6,
            f"{_DAY_FULL[day.weekday()]}, {day.strftime('%d.%m.%Y')}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        _table_header()
        for shift in day_shifts:
            if pdf.will_page_break(6):
                pdf.add_page()
                _table_header()
            _render_list_row(pdf, shift, employee_info, widths)
            pdf.ln()


def export_schedule_pdf(db: Session, schedule_id: int) -> bytes | None:
    """Generate a printable A4 landscape PDF for the given schedule.

    The PDF contains a cover page (summary + legend), one calendar page per
    week (A/B weeks separated) and a chronological shift list. Returns the PDF
    bytes or None if the schedule was not found.
    """
    schedule, shifts = _get_schedule_with_shifts(db, schedule_id)
    if not schedule:
        return None

    employee_info = _employee_info(db, {s.employee_id for s in shifts})

    pdf = _SchedulePdf(schedule.name, orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    _render_cover_page(pdf, schedule, shifts, employee_info)
    _render_calendar_pages(pdf, schedule, shifts, employee_info)
    _render_list_pages(pdf, shifts, employee_info)

    return bytes(pdf.output())
