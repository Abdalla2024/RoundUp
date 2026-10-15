"""R-1.9: the engine's generated purchases must equal the independent implementation's, written from the spec alone (AMB-25)."""

import pathlib
import sys
from datetime import date, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "crosscheck"))
import crosscheck as cc  # noqa: E402

from roundup_engine.money import parse_amount_cents  # noqa: E402
from roundup_engine.typical import typical_transactions  # noqa: E402


def engine_list(n, a, s, e):
    return [(r["posted_date"], parse_amount_cents(r["amount"])) for r in typical_transactions(n, a, s, e)]


def test_every_weekly_count_and_a_spread_of_averages_and_windows_agree():
    starts = [date(2024, 1, 1) + timedelta(days=k) for k in (0, 1, 2, 3, 4, 5, 6, 9, 31)]
    for n in range(1, 61):
        for a in (1, 25, 49, 50, 51, 99):
            for s in starts[::3] if n % 7 else starts:
                for span in (0, 1, 6, 7, 13, 27, 90):
                    e = s + timedelta(days=span)
                    assert engine_list(n, a, s.isoformat(), e.isoformat()) == cc.typical_purchases(n, a, s.isoformat(), e.isoformat()), (n, a, s, e)


def test_a_year_of_every_extreme_agrees():
    for n, a in [(1, 1), (1, 99), (60, 1), (60, 99), (7, 50), (13, 37), (59, 50)]:
        assert engine_list(n, a, "2024-01-01", "2024-12-29") == cc.typical_purchases(n, a, "2024-01-01", "2024-12-29")
