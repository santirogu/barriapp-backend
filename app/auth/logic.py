"""Pure, unit-tested auth logic (no I/O)."""

from datetime import date

MIN_AGE = 18


def calculate_age(birth_date: date, today: date) -> int:
    """Full years between ``birth_date`` and ``today`` (never negative-adjusted here)."""
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def is_adult(birth_date: date, today: date) -> bool:
    return calculate_age(birth_date, today) >= MIN_AGE
