from datetime import date, datetime, timezone


def parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()


def iso_week_number(d: date) -> int:
    return d.isocalendar()[1]


def iso_year(d: date) -> int:
    return d.isocalendar()[0]
