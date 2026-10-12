"""Synthetic trading calendar: weekdays minus the NYSE's regular holidays, computed by rule.

Not an official calendar: unscheduled closures (weather, national days of mourning) are not modelled.
"""

from datetime import date, timedelta


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _easter(year: int) -> date:
    """Anonymous Gregorian algorithm (integer arithmetic)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = (h + l_ - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _observed(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def holidays(year: int) -> set[date]:
    out = set()
    ny = date(year, 1, 1)
    if ny.weekday() == 6:
        out.add(ny + timedelta(days=1))
    elif ny.weekday() != 5:          # Saturday New Year's Day: not observed
        out.add(ny)
    out.add(_nth_weekday(year, 1, 0, 3))            # Martin Luther King Jr. Day
    out.add(_nth_weekday(year, 2, 0, 3))            # Washington's Birthday
    out.add(_easter(year) - timedelta(days=2))      # Good Friday
    out.add(_last_weekday(year, 5, 0))              # Memorial Day
    if year >= 2022:
        out.add(_observed(date(year, 6, 19)))       # Juneteenth
    out.add(_observed(date(year, 7, 4)))            # Independence Day
    out.add(_nth_weekday(year, 9, 0, 1))            # Labor Day
    out.add(_nth_weekday(year, 11, 3, 4))           # Thanksgiving
    out.add(_observed(date(year, 12, 25)))          # Christmas
    return out


def trading_calendar(start: date, end: date) -> list[date]:
    hol = set()
    for y in range(start.year, end.year + 1):
        hol |= holidays(y)
    out, d = [], start
    while d <= end:
        if d.weekday() < 5 and d not in hol:
            out.append(d)
        d += timedelta(days=1)
    return out
