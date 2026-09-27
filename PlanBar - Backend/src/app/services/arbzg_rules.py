"""Single source of truth for ArbZG (Arbeitszeitgesetz) rule parameters.

Both the manual-path validator (app.services.arbzg_validator) and the TiTO
callback processing (app.services.tito_callback) must apply the SAME legal
thresholds, and app.config reuses the same defaults for the solver payload.
This module is intentionally free of any app imports to avoid cycles.

Legal references (corrected mapping):
- § 2 Abs. 1 ArbZG: Ruhepausen do NOT count as working time (net hours)
- § 3 ArbZG:        max 10h daily working time, 48h weekly average (S. 2)
- § 4 ArbZG:        breaks: 30min for >6h up to 9h, 45min for >9h
- § 5 ArbZG:        11h uninterrupted rest between shifts
- § 3 + § 9 ArbZG:  max 6 consecutive working days (weekday rule)
- § 9/§ 11 ArbZG:   Sunday/holiday rest; >= 15 free Sundays per year
- § 6 ArbZG:        night work (10h limit, Eignungsuntersuchung)

JArbSchG (minors): 8h/day, 40h/week, 12h rest, no work 20:00-06:00,
no Saturday/Sunday/holiday work.
"""

# ── § 4 ArbZG: breaks ────────────────────────────────────────────────────────
BREAK_THRESHOLD_6H = 6  # § 4 – break required for "mehr als 6 bis zu 9 Stunden"
BREAK_MIN_30 = 30  # § 4 – minimum 30 min break for >6h
BREAK_THRESHOLD_9H = 9  # § 4 – extended break required for "mehr als 9 Stunden"
BREAK_MIN_45 = 45  # § 4 – minimum 45 min break for >9h

# ── § 3 ArbZG: daily / weekly maximum ────────────────────────────────────────
MAX_DAILY_HOURS = 10  # § 3 – maximum daily working time (net)
MAX_WEEKLY_HOURS_LAW = 48  # § 3 S. 2 – average weekly working time

# ── § 5 ArbZG: rest time ─────────────────────────────────────────────────────
MIN_REST_HOURS = 11  # § 5 – minimum uninterrupted rest between shifts

# ── § 3 + § 9 ArbZG: consecutive working days ────────────────────────────────
MAX_CONSECUTIVE_DAYS = 6  # consequence of § 3 (Werktage) + § 9 (Sunday rest)

# ── § 9/§ 11 ArbZG: Sundays / holidays ───────────────────────────────────────
MIN_FREE_SUNDAYS_PER_YEAR = 15  # § 9 – at least 15 free Sundays per year
SUNDAYS_PER_YEAR = 52

# ── § 6 ArbZG: night work ────────────────────────────────────────────────────
NIGHT_WINDOW_START = "23:00"  # § 6 – configurable night window start
NIGHT_WINDOW_END = "06:00"  # § 6 – configurable night window end
NIGHT_WORK_MAX_HOURS = 10  # § 6 Abs. 2 – max net hours for night workers

# ── JArbSchG (minors) ────────────────────────────────────────────────────────
MINOR_MAX_DAILY_HOURS = 8  # § 8 JArbSchG
MINOR_MAX_WEEKLY_HOURS = 40  # § 15 JArbSchG (shortened: 40h school-free days)
MINOR_MIN_REST_HOURS = 12  # § 9/§ 16 JArbSchG rest time
MINOR_NIGHT_REST_START = "20:00"  # § 10 JArbSchG night rest
MINOR_NIGHT_REST_END = "06:00"  # § 10 JArbSchG night rest

# ── § 11 Abs. 3 ArbZG: Ersatzruhetag deadlines ───────────────────────────────
ERSATZRUHETAG_SUNDAY_DAYS = 14  # free day within 2 calendar weeks after Sunday work
ERSATZRUHETAG_HOLIDAY_DAYS = 56  # free day within 8 weeks after holiday work


def required_break_minutes(duration_hours: float) -> int:
    """§ 4 ArbZG statutory break for a given (gross) shift duration in hours.

    "mehr als 6 bis zu 9 Stunden" -> 30 min total break
    "mehr als 9 Stunden"           -> 45 min total break
    up to and including 6 hours    -> no statutory break
    """
    if duration_hours > BREAK_THRESHOLD_9H:
        return BREAK_MIN_45
    if duration_hours > BREAK_THRESHOLD_6H:
        return BREAK_MIN_30
    return 0
