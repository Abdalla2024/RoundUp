"""Composition of the end value (R-13.4, stage 6, display only): four parts and their shares in basis points.

Shares are floor(amount * 10000 / ending value) for each part, worked out exactly (Fractions, no rounding), then the leftover basis points
(10000 minus the sum of the floors) go one each to the parts with the largest fractional remainders, ties to the earlier part. All zero when the
ending value is zero.
"""

from decimal import Decimal
from fractions import Fraction

KEYS = ("shares", "roundups_waiting", "dividends_as_cash", "receivables")


def share_bp(parts: list[Decimal], total: Decimal) -> list[int]:
    if total == 0:
        return [0] * len(parts)
    exact = [Fraction(p) * 10000 / Fraction(total) for p in parts]
    floors = [e.numerator // e.denominator for e in exact]
    leftover = 10000 - sum(floors)
    order = sorted(range(len(parts)), key=lambda i: (-(exact[i] - floors[i]), i))
    for i in order[:max(leftover, 0)]:
        floors[i] += 1
    return floors
