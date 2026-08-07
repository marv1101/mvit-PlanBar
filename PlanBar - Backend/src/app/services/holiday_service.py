"""German public holidays service.

Provides holiday date calculation for use in TiTO solver payload generation.
Uses the python-holidays library when available to compute both fixed and
movable German holidays (e.g. Easter, Pentecost) according to §9 ArbZG.
Falls back to a static list of fixed nationwide holidays if the library
is not installed.
"""

from datetime import date, timedelta

try:
    import holidays

    _HAS_HOLIDAYS = True
except ImportError:  # pragma: no cover
    _HAS_HOLIDAYS = False

# Fixed nationwide German holidays (YYYY-MM-DD without year)
_FIXED_NATIONWIDE: dict[tuple[int, int], str] = {
    (1, 1): "Neujahr",
    (5, 1): "Tag der Arbeit",
    (10, 3): "Tag der Deutschen Einheit",
    (12, 25): "Erster Weihnachtstag",
    (12, 26): "Zweiter Weihnachtstag",
}


def _get_fixed_holidays(start_date: date, end_date: date) -> list[str]:
    """Fallback that returns only fixed nationwide holidays."""
    result: list[str] = []
    current = start_date
    while current <= end_date:
        if (current.month, current.day) in _FIXED_NATIONWIDE:
            result.append(current.isoformat())
        current += timedelta(days=1)
    return result


def get_german_holidays(
    start_date: date,
    end_date: date,
    subdivision: str | None = None,
) -> list[str]:
    """Return a list of German public holiday dates in ISO format (YYYY-MM-DD).

    Args:
        start_date: inclusive start of the period
        end_date: inclusive end of the period
        subdivision: optional federal state code (e.g. 'BW', 'BY', 'BE').
                     When omitted, only nation-wide holidays are returned.

    Returns:
        Sorted list of holiday date strings.
    """
    if not _HAS_HOLIDAYS:
        return _get_fixed_holidays(start_date, end_date)

    years = list(range(start_date.year, end_date.year + 1))

    de_holidays = holidays.DE(subdiv=subdivision, years=years) if subdivision else holidays.DE(years=years)

    result: list[str] = []
    current = start_date
    while current <= end_date:
        if current in de_holidays:
            result.append(current.isoformat())
        current += timedelta(days=1)

    return result
