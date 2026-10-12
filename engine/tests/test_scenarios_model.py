"""Synthetic scenario generator (SCENARIO-MODEL.md): written before the generator."""

import pathlib
import re
from datetime import date
from decimal import Decimal

import pytest

from roundup_engine import run_scenario
from roundup_engine.generator import generate_transactions
from roundup_engine.market import validate_series
from roundup_scenarios import (FAMILIES, LABEL, MODEL_VERSION, STYLES, generate_series, market_dict,
                               published_scenarios, trading_calendar)

ROOT = pathlib.Path(__file__).resolve().parents[2]
ALL = [(f, s) for f in FAMILIES for s in STYLES]

# Real ticker symbols that must never appear in synthetic scenario text (owner: "never as a real fund").
REAL_TICKERS = {"VOO", "VTI", "SCHD", "VYM", "SPY", "IVV", "QQQ", "DIA", "VIG", "DGRO", "HDV", "NOBL",
                "ITOT", "SCHB", "SCHX", "VXUS", "BND", "AGG", "IWM", "VUG", "VTV", "VGT", "SPLG"}


def _text(series) -> str:
    m = series.meta
    return " ".join([series.market.symbol, m["name"], m["label"], m["description"], m["style_name"]])


# ---------------------------------------------------------------- determinism
@pytest.mark.parametrize("family,style", ALL)
def test_same_seed_identical(family, style):
    a, b = generate_series(family, style, seed=42), generate_series(family, style, seed=42)
    assert market_dict(a) == market_dict(b)
    assert a.market.checksum() == b.market.checksum()


@pytest.mark.parametrize("family,style", ALL)
def test_different_seed_differs(family, style):
    assert generate_series(family, style, seed=42).market.checksum() != \
        generate_series(family, style, seed=43).market.checksum()


def test_published_scenarios_fixed_seeds():
    pubs = published_scenarios()
    assert {p.meta["scenario_id"] for p in pubs} == set(FAMILIES)
    assert len(pubs) == len(FAMILIES) * len(STYLES)
    for p in pubs:
        assert p.meta["seed"] == FAMILIES[p.meta["scenario_id"]]["seed"]
        assert p.meta["model_version"] == MODEL_VERSION


# ---------------------------------------------------------------- calendar (NYSE 2026 list, nyse.com/markets/hours-calendars)
NYSE_2026_HOLIDAYS = ["2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
                      "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25"]


def test_calendar_matches_nyse_2026_regular_holidays():
    cal = set(trading_calendar(date(2026, 1, 1), date(2026, 12, 31)))
    for h in NYSE_2026_HOLIDAYS:
        assert date.fromisoformat(h) not in cal, h
    weekdays = [d for d in (date.fromordinal(o) for o in range(date(2026, 1, 1).toordinal(),
                                                               date(2026, 12, 31).toordinal() + 1))
                if d.weekday() < 5]
    assert len(cal) == len(weekdays) - len(NYSE_2026_HOLIDAYS)
    assert date(2026, 11, 27) in cal and date(2026, 12, 24) in cal   # early closes are sessions (R-5.6)


def test_calendar_2012_starts_on_jan_3():
    cal = trading_calendar(date(2012, 1, 1), date(2012, 1, 10))
    assert cal[0] == date(2012, 1, 3)


# ---------------------------------------------------------------- data rules
@pytest.mark.parametrize("family,style", ALL)
def test_prices_positive_and_four_decimals(family, style):
    s = generate_series(family, style, seed=7)
    for v in s.market.closes.values():
        assert v > 0
        assert -v.as_tuple().exponent <= 4


@pytest.mark.parametrize("family,style", ALL)
def test_dividends_and_splits_follow_engine_rules(family, style):
    s = generate_series(family, style, seed=7)
    m = s.market
    validate_series(m)                                    # R-6.3, R-7.5, R-8.7, R-8.8: raises on violation
    assert len(m.splits) >= 1                            # at least one split per series (so per family)
    years = (m.calendar[-1] - m.calendar[0]).days // 365
    assert len(m.dividends) >= years * 4 - 1             # quarterly
    for d in m.dividends:
        assert d.ex_date in m.closes and d.pay_date is not None and d.pay_date >= d.ex_date
        assert d.amount > 0
    ex_dates = {d.ex_date for d in m.dividends}
    for sp in m.splits:
        assert sp.ex_date not in ex_dates


def test_split_families_include_forward_and_reverse():
    ratios = {generate_series(f, "broad", seed=1).market.splits[0].ratio for f in FAMILIES}
    assert any(r > 1 for r in ratios) and any(r < 1 for r in ratios)


def test_no_floats_in_generated_values():
    s = generate_series("high-volatility", "dividend", seed=3)
    for v in [*s.market.closes.values(), *(d.amount for d in s.market.dividends),
              *(x.ratio for x in s.market.splits)]:
        assert isinstance(v, Decimal)


# ---------------------------------------------------------------- the engine accepts every generated series
@pytest.mark.parametrize("family,style", ALL)
@pytest.mark.parametrize("strategy", ["threshold", "next_session", "weekly", "monthly"])
def test_engine_accepts_full_range(family, style, strategy):
    s = generate_series(family, style, seed=FAMILIES[family]["seed"])
    m = market_dict(s)
    txs = generate_transactions(seed=99, start="2012-01-03", end="2026-09-30", max_per_day=1)
    out = run_scenario({"id": "t", "market": m, "transactions": txs,
                        "config": {"strategy": strategy, "start": "2012-01-03", "end": "2026-09-30",
                                   "reinvest": "true"}})
    assert out["status"] == "ok", out["error_code"]
    assert int(out["summary"]["roundup_buys"]) > 0 and int(out["summary"]["dividend_buys"]) > 0


# ---------------------------------------------------------------- labelling
@pytest.mark.parametrize("family,style", ALL)
def test_no_real_ticker_names_and_labelled_synthetic(family, style):
    s = generate_series(family, style, seed=FAMILIES[family]["seed"])
    words = set(re.findall(r"[A-Za-z]+", _text(s)))
    assert not (words & REAL_TICKERS), words & REAL_TICKERS
    assert s.market.symbol.startswith("SYN-")
    assert s.market.kind == "sample"
    assert s.meta["label"] == LABEL
    assert "Synthetic" in LABEL and "not a forecast" in LABEL and "Not a real fund" in LABEL


def test_regimes_behave_as_named():
    """Sanity on the published seeds only: the names describe what the series does."""
    def path(f):
        m = generate_series(f, "broad", seed=FAMILIES[f]["seed"]).market
        return [m.closes[d] * _split_factor(m, d) for d in m.calendar if d in m.closes]

    steady, crash = path("steady-growth"), path("crash-and-recovery")
    assert steady[-1] > steady[0] * 2
    peak = max(crash[: len(crash) // 2])
    trough = min(crash[len(crash) * 30 // 100: len(crash) * 40 // 100])
    assert trough < peak * Decimal("0.75")               # a real crash (> 25% drawdown)


def _split_factor(m, d):
    f = Decimal(1)
    for s in m.splits:
        if d >= s.ex_date:
            f *= s.ratio                                 # undo splits to compare price levels
    return f


def test_model_document_lists_every_family_and_version():
    doc = (ROOT / "SCENARIO-MODEL.md").read_text()
    assert MODEL_VERSION in doc
    for f, p in FAMILIES.items():
        assert f"`{f}`" in doc and str(p["seed"]) in doc
