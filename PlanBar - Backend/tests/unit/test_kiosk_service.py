"""Tests for kiosk board service helpers."""

from datetime import date, datetime, timedelta, timezone

from app.services.kiosk_service import compute_kiosk_window


def test_compute_kiosk_window_from_wednesday():
    """A Wednesday yields Monday of this ISO week through Sunday of next week (14 days)."""
    window_start, window_end = compute_kiosk_window(date(2026, 9, 23))

    assert window_start == date(2026, 9, 21)
    assert window_end == date(2026, 10, 4)
    assert (window_end - window_start + timedelta(days=1)).days == 14


def test_compute_kiosk_window_from_monday_starts_same_day():
    """A Monday input starts the window on that same day."""
    window_start, window_end = compute_kiosk_window(date(2026, 9, 21))

    assert window_start == date(2026, 9, 21)
    assert window_end == date(2026, 10, 4)


def test_compute_kiosk_window_from_sunday_ends_next_sunday():
    """A Sunday input ends the window on that day plus 7 days."""
    window_start, window_end = compute_kiosk_window(date(2026, 9, 27))

    assert window_end == window_start + timedelta(days=7) + timedelta(days=6)
    assert window_end == date(2026, 9, 27) + timedelta(days=7)


def test_compute_kiosk_window_default_today():
    """Without an explicit today the window is based on the real current date."""
    today = datetime.now(tz=timezone.utc).date()
    expected_start = today - timedelta(days=today.weekday())

    window_start, window_end = compute_kiosk_window()

    assert window_start == expected_start
    assert window_end == expected_start + timedelta(days=13)
