"""Property tests over seeded random scenarios (Hypothesis picks the seeds and shrinks failures).

Covers: round-ups never negative (P-01), contributions = sum of round-ups (P-02), no money created
or lost (P-03), execution strictly after cut-off (P-04, R-11.1), order independence (P-05),
no look-ahead under truncation (P-06, R-11.2), split invariance (P-07), constant-price identity (P-08),
dividend conservation (P-09), and independent fund runs (R-5.7).
"""

import copy
import random
from datetime import date
from decimal import Decimal, localcontext

from hypothesis import given, settings
from hypothesis import strategies as st
from random_scenarios import generate

from roundup_engine import run_scenario
from roundup_engine.money import CONTEXT, parse_amount_cents
from roundup_engine.roundup import roundup_cents
from roundup_engine.scenario import parse_scenario
from roundup_engine.simulate import simulate

SEEDS = st.integers(min_value=0, max_value=10**9)
TINY = Decimal("1e-18")


def _sim(s):
    market, txs, cfg = parse_scenario(s)
    return simulate(market, txs, cfg)


@given(st.integers(min_value=1, max_value=10**9))
def test_p01_roundup_never_negative_and_reaches_dollar(cents):
    r = roundup_cents(cents)
    assert 0 <= r <= 99 and (cents + r) % 100 == 0


@settings(max_examples=150, deadline=None)
@given(SEEDS)
def test_p02_contributions_equal_sum_of_roundups(seed):
    s = generate(seed)
    res = _sim(s)
    start, end = date.fromisoformat(s["config"]["start"]), date.fromisoformat(s["config"]["end"])
    expected = 0
    for t in s["transactions"]:  # independent re-derivation from the raw rows
        try:
            cents = parse_amount_cents(t["amount"])
        except Exception:
            continue
        if (t["direction"] == "debit" and t["status"] == "posted" and t["description"] != "ATM WITHDRAWAL"
                and cents > 0 and start <= date.fromisoformat(t["posted_date"]) <= end):
            expected += roundup_cents(cents)
    assert res.contributed_cents == expected
    # every round-up is either bought or still uninvested, exactly (integer cents)
    bought = sum(b.cash_cents for b in res.buys if b.kind == "roundup")
    assert bought + res.roundup_uninvested_cents == res.contributed_cents
    assert all(b.cash > 0 and b.shares > 0 for b in res.buys)


@settings(max_examples=150, deadline=None)
@given(SEEDS)
def test_p03_no_money_created_or_lost(seed):
    """ending value == contributed + dividends earned + market gains on each buy, computed independently."""
    s = generate(seed)
    res = _sim(s)
    splits = [(date.fromisoformat(x["ex_date"]), Decimal(x["ratio"])) for x in s["market"]["splits"]]
    with localcontext(CONTEXT):
        gains = Decimal(0)
        for b in res.buys:
            factor = Decimal(1)
            for ex, r in splits:
                if b.date < ex <= res.as_of:
                    factor *= r
            gains += b.cash * (res.last_price * factor / b.price) - b.cash
        expected = Decimal(res.contributed_cents) / 100 + res.dividends_earned + gains
    assert abs(res.ending_value - expected) < TINY
    # components add up exactly to the ending value
    assert abs(res.holdings_value + res.uninvested_cash + res.receivables - res.ending_value) < TINY


@settings(max_examples=150, deadline=None)
@given(SEEDS)
def test_p04_execution_strictly_after_cutoff(seed):
    res = _sim(generate(seed))
    for b in res.buys:
        if b.kind == "roundup":
            assert b.cutoff < b.date
            assert all(p <= b.cutoff for p in b.purchase_dates)
        else:
            assert b.pay_date <= b.date


@settings(max_examples=100, deadline=None)
@given(SEEDS, st.integers(min_value=0, max_value=10**6))
def test_p05_row_order_does_not_matter(seed, shuffle_seed):
    s = generate(seed)
    t = copy.deepcopy(s)
    random.Random(shuffle_seed).shuffle(t["transactions"])
    assert run_scenario(s) == run_scenario(t)


@settings(max_examples=100, deadline=None)
@given(SEEDS, st.integers(min_value=0, max_value=30))
def test_p06_truncating_future_data_changes_nothing_before_cut(seed, k):
    """R-11.2: run to end T, vs the same with all market data after T removed."""
    s = generate(seed)
    cal = [d for d in s["market"]["calendar"] if s["config"]["start"] <= d <= s["config"]["end"]]
    T = cal[min(k, len(cal) - 1)]
    if T not in s["market"]["closes"]:
        return  # end must be a day with a close for the truncated run to be valid
    a = copy.deepcopy(s)
    a["config"]["end"] = T
    b = copy.deepcopy(a)
    m = b["market"]
    m["calendar"] = [d for d in m["calendar"] if d <= T]
    m["closes"] = {d: v for d, v in m["closes"].items() if d <= T}
    m["dividends"] = [x for x in m["dividends"] if x["ex_date"] <= T]
    m["splits"] = [x for x in m["splits"] if x["ex_date"] <= T]
    ra, rb = run_scenario(a), run_scenario(b)
    assert ra["status"] == rb["status"] == "ok"
    assert ra == rb


@settings(max_examples=100, deadline=None)
@given(SEEDS, st.sampled_from(["2", "4", "0.5"]), st.integers(min_value=5, max_value=40))
def test_p07_inserting_a_split_changes_no_value(seed, ratio, idx):
    s = generate(seed)
    if s["market"]["splits"]:
        return
    cal = [d for d in s["market"]["calendar"] if d in s["market"]["closes"]]
    S = cal[min(idx, len(cal) - 2)]
    t = copy.deepcopy(s)
    r = Decimal(ratio)
    with localcontext(CONTEXT):
        t["market"]["closes"] = {d: (str(Decimal(v) / r) if d >= S else v) for d, v in s["market"]["closes"].items()}
        for x in t["market"]["dividends"]:
            if x["ex_date"] >= S:
                x["amount_raw"] = str(Decimal(x["amount_raw"]) / r)
    t["market"]["splits"] = [{"ex_date": S, "ratio": ratio}]
    ra, rb = _sim(s), _sim(t)
    assert abs(ra.ending_value - rb.ending_value) < TINY
    assert abs(ra.dividends_earned - rb.dividends_earned) < TINY
    for pa, pb in zip(ra.series, rb.series):
        assert abs(pa.value - pb.value) < TINY


@settings(max_examples=100, deadline=None)
@given(SEEDS)
def test_p08_constant_price_no_dividends_value_equals_contributions(seed):
    s = generate(seed)
    s["market"]["closes"] = {d: "37.00" for d in s["market"]["closes"]}
    s["market"]["dividends"], s["market"]["splits"] = [], []
    res = _sim(s)
    assert abs(res.ending_value - Decimal(res.contributed_cents) / 100) < TINY
    for p in res.series:
        assert p.value >= 0


@settings(max_examples=150, deadline=None)
@given(SEEDS)
def test_p09_dividends_conserved(seed):
    """Every dividend earned is reinvested, held as cash, or still receivable: never twice, never lost."""
    res = _sim(generate(seed))
    reinvested = sum((b.cash for b in res.buys if b.kind == "dividend"), Decimal(0))
    total = reinvested + res.dividend_cash + res.receivables
    assert abs(total - res.dividends_earned) < TINY
    assert res.dividends_paid <= res.dividends_earned


@settings(max_examples=50, deadline=None)
@given(SEEDS, SEEDS)
def test_r_5_7_fund_runs_are_independent(seed_a, seed_b):
    """Running fund A is unaffected by anything about fund B (no shared state between runs)."""
    a, b = generate(seed_a), generate(seed_b)
    first = run_scenario(a)
    run_scenario(b)
    assert run_scenario(a) == first


def test_regression_r5288_half_cent_tie_in_series():
    """Found by the independent cross-check: the exact value on 2024-07-24 is 9.485 (a tie)."""
    s = generate(5288, n_days=40 + 5288 % 60)
    out = run_scenario(s)
    point = [p for p in out["series"] if p["date"] == "2024-07-24"][0]
    assert point["value"] == "9.48"
