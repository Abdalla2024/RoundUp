"""Batching strategies (FINANCE-RULES R-5.1, R-5.2)."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta

THRESHOLD_CENTS = 500   # R-5.2: fixed at $5.00 in v1
STRATEGIES = ("threshold", "next_session", "weekly", "monthly")


@dataclass(frozen=True)
class Batch:
    cutoff: date
    cents: int
    purchase_dates: tuple[date, ...]


def make_batches(roundups: list[tuple[date, int]], strategy: str) -> tuple[list[Batch], int]:
    """Group non-zero round-ups into batches.

    Returns (batches sorted by cut-off, cents never batched). Only the threshold strategy can
    leave cents unbatched (a final partial batch); they stay uninvested cash (R-5.4).
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}")
    by_day: dict[date, int] = {}
    for day, cents in roundups:
        if cents > 0:
            by_day[day] = by_day.get(day, 0) + cents

    if strategy == "threshold":
        batches, acc, members = [], 0, []
        for day in sorted(by_day):
            acc += by_day[day]
            members.append(day)
            if acc >= THRESHOLD_CENTS:
                batches.append(Batch(day, acc, tuple(members)))
                acc, members = 0, []
        return batches, acc

    def cutoff(day: date) -> date:
        if strategy == "next_session":
            return day
        if strategy == "weekly":                       # Monday-Sunday weeks; cut-off Sunday
            return day + timedelta(days=6 - day.weekday())
        return date(day.year, day.month, monthrange(day.year, day.month)[1])  # monthly

    groups: dict[date, list[date]] = {}
    for day in by_day:
        groups.setdefault(cutoff(day), []).append(day)
    batches = [Batch(c, sum(by_day[d] for d in days), tuple(sorted(days))) for c, days in groups.items()]
    return sorted(batches, key=lambda b: b.cutoff), 0
