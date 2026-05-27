from datetime import date

from app.utils.helpers import iso_week_number, iso_year, parse_date


def test_parse_date_from_string():
    result = parse_date("2026-05-27")
    assert result == date(2026, 5, 27)


def test_parse_date_from_date():
    d = date(2026, 5, 27)
    result = parse_date(d)
    assert result == d


def test_iso_week_number():
    d = date(2026, 5, 27)
    assert iso_week_number(d) == 22


def test_iso_year():
    d = date(2026, 5, 27)
    assert iso_year(d) == 2026


def test_iso_year_early_january():
    d = date(2027, 1, 1)
    assert iso_year(d) == 2026
