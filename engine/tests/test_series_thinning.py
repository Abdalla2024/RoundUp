"""Chart thinning (owner decision, stage 4): daily points for ranges up to about a year, weekly points for longer
ranges. Thinning happens only in the engine's output; every number is still computed daily."""

import copy
from datetime import date, timedelta

import pytest
from random_scenarios import generate

from roundup_engine import run_scenario
from roundup_engine.generator import generate_transactions
from roundup_scenarios import FAMILIES, STYLES, generate_series, market_dict

RULE = ("Chart shows daily values for ranges up to 366 days and one value per week (the week's last trading day) "
        "for longer ranges. All figures are calculated daily.")


def _scenario(start, end, family="crash-and-recovery", style="dividend", seed=5, strategy="weekly"):
    m = market_dict(generate_series(family, style, seed))
    return {"id": "t", "market": m,
            "transactions": generate_transactions(seed=seed, start=start, end=end, max_per_day=2),
            "config": {"strategy": strategy, "start": start, "end": end, "reinvest": "true"}}


def _without_series(r):
    return {k: v for k, v in r.items() if k not in ("series", "series_resolution", "series_rule")}


def test_default_is_daily_and_unchanged_format():
    s = _scenario("2015-01-02", "2019-12-31")
    r = run_scenario(s)
    assert "series_resolution" not in r                     # FORMAT.md default: full daily series
    cal = [d for d in s["market"]["calendar"] if "2015-01-02" <= d <= "2019-12-31"]
    assert [p["date"] for p in r["series"]] == cal


@pytest.mark.parametrize("days,expected", [(30, "daily"), (365, "daily"), (366, "daily"), (367, "weekly"),
                                           (3000, "weekly")])
def test_auto_resolution_boundary(days, expected):
    start = date(2014, 3, 3)
    end = (start + timedelta(days=days)).isoformat()
    r = run_scenario(_scenario(start.isoformat(), end), series="auto")
    assert r["series_resolution"] == expected and r["series_rule"] == RULE


def test_short_range_auto_equals_daily():
    s = _scenario("2016-02-01", "2016-12-30")
    daily, auto = run_scenario(s), run_scenario(s, series="auto")
    assert auto["series"] == daily["series"]
    assert _without_series(auto) == _without_series(daily)


def _check_weekly(s):
    daily, auto = run_scenario(s), run_scenario(s, series="auto")
    assert auto["series_resolution"] == "weekly"
    # totals, buys and counts are unchanged: thinning touches only the chart points
    assert _without_series(auto) == _without_series(daily)
    by_date = {p["date"]: p for p in daily["series"]}
    days = [date.fromisoformat(p["date"]) for p in daily["series"]]
    expected = [d for i, d in enumerate(days) if i == len(days) - 1 or days[i + 1].isocalendar()[:2] != d.isocalendar()[:2]]
    assert [p["date"] for p in auto["series"]] == [d.isoformat() for d in expected]
    for p in auto["series"]:
        assert p == by_date[p["date"]]                       # identical value and carried flag
    assert auto["series"][-1] == daily["series"][-1]          # the final value is always shown


def test_long_range_weekly_points_are_daily_points():
    _check_weekly(_scenario("2012-01-03", "2026-09-30"))


@pytest.mark.parametrize("family", list(FAMILIES))
@pytest.mark.parametrize("style", list(STYLES))
def test_weekly_on_every_published_series(family, style):
    _check_weekly(_scenario("2013-06-03", "2018-06-29", family=family, style=style, seed=FAMILIES[family]["seed"],
                            strategy="threshold"))


@pytest.mark.parametrize("seed", range(30))
def test_weekly_with_gaps_and_random_markets(seed):
    s = generate(seed, n_days=400)                           # random markets incl. gaps (carried points)
    span = (date.fromisoformat(s["config"]["end"]) - date.fromisoformat(s["config"]["start"])).days
    if span <= 366:
        assert run_scenario(s, series="auto")["series_resolution"] == "daily"
        return
    _check_weekly(s)


def test_errors_unaffected():
    s = _scenario("2012-01-03", "2026-09-30")
    s["config"]["start"] = "2011-01-03"
    assert run_scenario(s, series="auto") == run_scenario(s)


def test_invalid_series_mode():
    with pytest.raises(ValueError):
        run_scenario(_scenario("2015-01-02", "2015-03-31"), series="monthly")


def test_size_reduction_full_range():
    s = _scenario("2012-01-03", "2026-09-30")
    assert len(run_scenario(s, series="auto")["series"]) * 4 < len(run_scenario(s)["series"])


def test_deep_copy_input_untouched():
    s = _scenario("2012-01-03", "2014-12-31")
    before = copy.deepcopy(s)
    run_scenario(s, series="auto")
    assert s == before
