"""Rule R-1.9, typical spending (stage 6): unit tests worked by hand, and properties."""

from datetime import date, timedelta

import pytest
from hypothesis import given, settings, strategies as st

from builders import closes, typical_scenario, weekdays
from roundup_engine.roundup import roundup_cents
from roundup_engine.money import parse_amount_cents
from roundup_engine.scenario import input_checksum, run_scenario
from roundup_engine.typical import typical_transactions


def rows(n, a, start, end):
    return typical_transactions(n, a, start, end)


def day_index(r):
    return (date.fromisoformat(r["posted_date"]) - date.fromisoformat("2024-01-01")).days % 7     # 2024-01-01 is a Monday


def test_five_a_week_lands_on_mon_tue_wed_fri_sat():
    out = rows(5, 50, "2024-01-01", "2024-01-14")
    assert [r["posted_date"] for r in out] == ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-05", "2024-01-06",
                                               "2024-01-08", "2024-01-09", "2024-01-10", "2024-01-12", "2024-01-13"]
    assert {r["amount"] for r in out} == {"12.50"}
    assert all(r["direction"] == "debit" and r["status"] == "posted" and r["category"] == "purchase" for r in out)


def test_seven_a_week_is_one_a_day_and_one_a_week_is_mondays():
    assert [r["posted_date"] for r in rows(7, 50, "2024-01-01", "2024-01-07")] == [f"2024-01-0{i}" for i in range(1, 8)]
    assert [r["posted_date"] for r in rows(1, 50, "2024-01-01", "2024-01-28")] == ["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22"]


def test_sixty_a_week_spreads_9_9_8_9_8_9_8():
    out = rows(60, 99, "2024-01-01", "2024-01-07")
    assert len(out) == 60
    assert [sum(1 for r in out if day_index(r) == d) for d in range(7)] == [9, 9, 8, 9, 8, 9, 8]


def test_ten_a_week_spreads_over_days_0_0_1_2_2_3_4_4_5_6():
    out = rows(10, 25, "2024-01-01", "2024-01-07")
    assert [day_index(r) for r in out] == [0, 0, 1, 2, 2, 3, 4, 4, 5, 6]


def test_amount_makes_the_round_up_exactly_the_average():
    for a, amount in [(1, "12.99"), (25, "12.75"), (50, "12.50"), (99, "12.01")]:
        r = rows(1, a, "2024-01-01", "2024-01-01")[0]
        assert r["amount"] == amount and roundup_cents(parse_amount_cents(r["amount"])) == a


def test_a_start_in_mid_week_drops_earlier_purchases_and_shifts_none():
    full = {r["posted_date"] for r in rows(5, 50, "2024-01-01", "2024-01-14")}
    mid = [r["posted_date"] for r in rows(5, 50, "2024-01-03", "2024-01-14")]
    assert mid == sorted(d for d in full if d >= "2024-01-03") and len(mid) == 8


def test_an_end_in_mid_week_drops_later_purchases():
    assert [r["posted_date"] for r in rows(5, 50, "2024-01-01", "2024-01-03")] == ["2024-01-01", "2024-01-02", "2024-01-03"]


@pytest.mark.parametrize("n,a", [(0, 50), (61, 50), (-1, 50), (5, 0), (5, 100), (5, -3)])
def test_inputs_out_of_range_are_rejected(n, a):
    with pytest.raises(ValueError):
        typical_transactions(n, a, "2024-01-01", "2024-01-07")


@pytest.mark.parametrize("per_week,avg", [("0", "0.50"), ("61", "0.50"), ("5.5", "0.50"), ("five", "0.50"), ("5", "0.00"), ("5", "1.00"),
                                          ("5", "0.5"), ("5", "0.505"), ("5", ".50"), ("5", "-0.50"), (" 5", "0.50")])
def test_scenario_inputs_must_be_whole_weekly_count_and_two_decimal_cents(per_week, avg):
    cal = weekdays("2024-01-01", "2024-01-31")
    s = typical_scenario("x", cal, closes(cal, [("2024-01-01", "50.00")]), 5, "0.50", "threshold", "2024-01-01", "2024-01-14")
    s["typical"] = {"per_week": per_week, "average_roundup": avg}
    with pytest.raises(ValueError):
        run_scenario(s)


def test_typical_and_explicit_transactions_together_are_rejected():
    cal = weekdays("2024-01-01", "2024-01-31")
    s = typical_scenario("x", cal, closes(cal, [("2024-01-01", "50.00")]), 5, "0.50", "threshold", "2024-01-01", "2024-01-14")
    s["transactions"] = []
    with pytest.raises(ValueError):
        run_scenario(s)


def test_a_typical_run_equals_the_same_run_with_the_purchases_written_out():
    cal = weekdays("2024-01-01", "2024-03-29", closed=("2024-01-15", "2024-02-19"))
    market = closes(cal, [("2024-01-01", "50.00")])
    for n, a, start, end, strat in [(5, "0.50", "2024-01-01", "2024-02-25", "threshold"), (7, "0.25", "2024-01-03", "2024-03-10", "weekly"),
                                    (13, "0.99", "2024-01-02", "2024-03-29", "monthly"), (1, "0.01", "2024-01-01", "2024-01-28", "next_session")]:
        t = typical_scenario("t", cal, market, n, a, strat, start, end)
        explicit = {**t, "transactions": typical_transactions(n, int(a.split(".")[1]), start, end)}
        del explicit["typical"]
        assert run_scenario(t) == run_scenario(explicit), (n, a, start, end)
        assert input_checksum(t) == input_checksum(explicit)


def test_the_checksum_changes_with_the_inputs_and_not_with_a_repeat():
    cal = weekdays("2024-01-01", "2024-01-31")
    mk = lambda n, a: typical_scenario("t", cal, closes(cal, [("2024-01-01", "50.00")]), n, a, "threshold", "2024-01-01", "2024-01-28")
    assert input_checksum(mk(5, "0.50")) == input_checksum(mk(5, "0.50"))
    assert len({input_checksum(mk(5, "0.50")), input_checksum(mk(6, "0.50")), input_checksum(mk(5, "0.51"))}) == 3


# ---------------------------------------------------------------- properties
weeks = st.integers(min_value=1, max_value=60)
avgs = st.integers(min_value=1, max_value=99)
mondays = st.integers(min_value=0, max_value=400).map(lambda k: date(2023, 1, 2) + timedelta(days=7 * k))          # 2023-01-02 is a Monday


@settings(max_examples=150, deadline=None)
@given(n=weeks, a=avgs, monday=mondays, w=st.integers(min_value=1, max_value=12))
def test_p_whole_weeks_hold_exactly_n_times_w_purchases_and_n_w_a_cents(n, a, monday, w):
    out = typical_transactions(n, a, monday.isoformat(), (monday + timedelta(days=7 * w - 1)).isoformat())
    assert len(out) == n * w
    assert sum(roundup_cents(parse_amount_cents(r["amount"])) for r in out) == n * w * a          # contributions = purchases x average


@settings(max_examples=150, deadline=None)
@given(n=weeks, a=avgs, monday=mondays)
def test_p_the_spread_rule_never_loses_or_duplicates_a_purchase(n, a, monday):
    out = typical_transactions(n, a, monday.isoformat(), (monday + timedelta(days=6)).isoformat())
    days = [(date.fromisoformat(r["posted_date"]) - monday).days for r in out]
    assert days == [(7 * k) // n for k in range(n)]               # purchase k of n on day floor(7k/n), in order
    assert all(0 <= d <= 6 for d in days) and days == sorted(days)


@settings(max_examples=150, deadline=None)
@given(n=weeks, a=avgs, start=mondays, s_off=st.integers(0, 40), e_off=st.integers(0, 120), more=st.integers(0, 60), before=st.integers(0, 40))
def test_p_no_look_ahead_and_the_start_date_never_moves_a_purchase(n, a, start, s_off, e_off, more, before):
    s = start + timedelta(days=s_off)
    e = s + timedelta(days=e_off)
    base = typical_transactions(n, a, s.isoformat(), e.isoformat())
    longer = typical_transactions(n, a, s.isoformat(), (e + timedelta(days=more)).isoformat())
    assert base == [r for r in longer if r["posted_date"] <= e.isoformat()]                      # later days change nothing earlier
    earlier = typical_transactions(n, a, (s - timedelta(days=before)).isoformat(), e.isoformat())
    assert base == [r for r in earlier if r["posted_date"] >= s.isoformat()]                     # the start only cuts, never shifts


@settings(max_examples=100, deadline=None)
@given(n=weeks, a=avgs, start=mondays, e_off=st.integers(0, 100))
def test_p_every_purchase_is_a_posted_debit_purchase_with_round_up_a_inside_the_window(n, a, start, e_off):
    e = start + timedelta(days=e_off)
    for r in typical_transactions(n, a, start.isoformat(), e.isoformat()):
        assert start.isoformat() <= r["posted_date"] <= e.isoformat()
        assert (r["direction"], r["status"], r["category"]) == ("debit", "posted", "purchase")
        assert roundup_cents(parse_amount_cents(r["amount"])) == a
