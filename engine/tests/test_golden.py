"""Golden scenarios (tests/golden_cases.py): hand-computed expectations, checked field by field."""

import pytest
from golden_cases import CASES

from roundup_engine import run_scenario


@pytest.mark.parametrize("c", CASES, ids=[c["scenario"]["id"] for c in CASES])
def test_golden(c):
    out = run_scenario(c["scenario"])
    exp = c["expect"]
    assert out["status"] == exp.get("status", "ok"), out.get("error_code")
    if "error_code" in exp:
        assert out["error_code"] == exp["error_code"]
        assert out["summary"] is None and out["buys"] is None and out["series"] is None
        return
    for key, value in exp.get("summary", {}).items():
        assert out["summary"][key] == value, key
    if "buys" in exp:
        assert len(out["buys"]) == len(exp["buys"])
        for got, want in zip(out["buys"], exp["buys"]):
            for key, value in want.items():
                assert got[key] == value, (key, got)
    if "series" in exp:
        by_date = {p["date"]: p for p in out["series"]}
        for day, (value, carried) in exp["series"].items():
            assert (by_date[day]["value"], by_date[day]["carried"]) == (value, carried), day
    for key in ("transactions_used", "transactions_ignored"):
        if key in exp:
            assert out[key] == exp[key], key


def test_every_case_names_rules():
    for c in CASES:
        assert c["scenario"]["covers"], c["scenario"]["id"]


def test_series_has_one_point_per_calendar_open_day():
    s = CASES[0]["scenario"]
    out = run_scenario(s)
    cal = [d for d in s["market"]["calendar"] if s["config"]["start"] <= d <= s["config"]["end"]]
    assert [p["date"] for p in out["series"]] == cal


def test_rule_coverage():
    """Every non-OPEN engine rule in FINANCE-RULES.md is covered by a golden case or a named unit test."""
    covered = {r for c in CASES for r in c["scenario"]["covers"]}
    covered |= UNIT_TESTED
    missing = sorted(ENGINE_RULES - covered)
    assert not missing, missing


# Rules enforced by unit/property tests elsewhere (see the named test modules).
UNIT_TESTED = {
    "R-0.1", "R-0.3", "R-0.4", "R-0.5",          # test_money.py, test_no_floats.py
    "R-1.2", "R-1.3", "R-1.5", "R-1.7",          # test_importing.py
    "R-4.1", "R-4.2", "R-4.3", "R-4.4", "R-4.5",  # test_importing.py
    "R-5.5", "R-11.1", "R-11.2",                 # test_properties.py (no look-ahead, truncation)
    "R-5.7",                                     # test_properties.py (independent runs)
}
# Engine-scope rules (others are UI, data-stage, disclosure, or out-of-scope statements).
ENGINE_RULES = {
    "R-0.1", "R-0.3", "R-0.4", "R-0.5",
    "R-1.2", "R-1.3", "R-1.4", "R-1.5", "R-1.6", "R-1.7", "R-1.8",
    "R-2.1", "R-2.2", "R-3.1", "R-3.2",
    "R-4.1", "R-4.2", "R-4.3", "R-4.4", "R-4.5",
    "R-5.1", "R-5.2", "R-5.3", "R-5.4", "R-5.5", "R-5.6", "R-5.7",
    "R-6.2", "R-6.3", "R-6.4", "R-6.5",
    "R-7.4", "R-7.5",
    "R-8.1", "R-8.2", "R-8.3", "R-8.4", "R-8.5", "R-8.6", "R-8.7", "R-8.8",
    "R-9.1", "R-11.1", "R-11.2", "R-12.1", "R-13.1", "R-13.2",
}
