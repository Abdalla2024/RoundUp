"""Engine-side comparison (the API must not calculate), input checksum, and the R-1.4 category override."""

import copy

from golden_cases import CASES
from random_scenarios import generate

from roundup_engine import run_scenario
from roundup_engine.compare import compare_scenarios
from roundup_engine.scenario import input_checksum

G21 = next(c["scenario"] for c in CASES if c["scenario"]["id"] == "G-21")


def _with(s, **cfg):
    t = copy.deepcopy(s)
    t["config"].update(cfg)
    return t


def test_compare_returns_both_engine_results_unchanged():
    out = compare_scenarios(G21, {"strategy": "next_session", "reinvest": "true"},
                            {"strategy": "next_session", "reinvest": "false"})
    assert out["a"] == run_scenario(_with(G21, reinvest="true"))
    assert out["b"] == run_scenario(_with(G21, reinvest="false"))


def test_compare_difference_hand_checked():
    # G-21 vs G-24: reinvesting the $0.20 dividend at 9.60 then valuing at 9.60 changes nothing (5.00 vs 5.00);
    # uninvested cash 0.00 vs 0.20; dividend buys 1 vs 0.
    d = compare_scenarios(G21, {"strategy": "next_session", "reinvest": "true"},
                          {"strategy": "next_session", "reinvest": "false"})["difference"]
    assert d == {"ending_value": "0.00", "gain": "0.00", "dividends_earned": "0.00", "uninvested_cash": "0.20",
                 "roundup_buys": "0", "dividend_buys": "-1"}


def test_compare_same_config_is_zero_and_symmetric():
    for seed in range(20):
        s = generate(seed)
        cfg = {"strategy": s["config"]["strategy"], "reinvest": s["config"]["reinvest"]}
        other = {"strategy": "monthly", "reinvest": "false"}
        assert set(compare_scenarios(s, cfg, cfg)["difference"].values()) <= {"0.00", "0"}
        ab = compare_scenarios(s, cfg, other)["difference"]
        ba = compare_scenarios(s, other, cfg)["difference"]
        for k in ab:
            neg = ab[k][1:] if ab[k].startswith("-") else ("-" + ab[k] if ab[k] not in ("0", "0.00") else ab[k])
            assert ba[k] == neg, k


def test_compare_error_has_no_difference():
    s = _with(G21, start="2023-12-01")
    out = compare_scenarios(s, {"strategy": "threshold", "reinvest": "true"},
                            {"strategy": "weekly", "reinvest": "true"})
    assert out["a"]["error_code"] == "WINDOW_OUTSIDE_DATA" and out["difference"] is None


def test_input_checksum_stable_and_sensitive():
    a = input_checksum(G21)
    assert a == input_checksum(copy.deepcopy(G21)) and len(a) == 64
    assert input_checksum(_with(G21, reinvest="false")) != a
    t = copy.deepcopy(G21)
    t["transactions"][0]["amount"] = "1.51"
    assert input_checksum(t) != a
    m = copy.deepcopy(G21)
    m["market"]["closes"]["2024-01-31"] = "9.61"
    assert input_checksum(m) != a


def test_r_1_4_category_override():
    s = copy.deepcopy(G21)
    s["transactions"] = [{"posted_date": "2024-01-08", "amount": "4.37", "direction": "debit", "status": "posted",
                          "type": "", "description": "ATM WITHDRAWAL", "category": "purchase"},
                         {"posted_date": "2024-01-08", "amount": "3.37", "direction": "debit", "status": "posted",
                          "type": "", "description": "COFFEE", "category": "non_purchase"}]
    out = run_scenario(s)
    assert out["summary"]["contributed"] == "0.63"
    assert out["transactions_used"] == "1" and out["transactions_ignored"] == "1"


def test_input_checksum_uses_resolved_category_not_description():
    """Found by the independent API tester: merchant text must not feed a stored hash (D-8)."""
    a, b, c = copy.deepcopy(G21), copy.deepcopy(G21), copy.deepcopy(G21)
    for t in b["transactions"]:
        t["description"] = "SOME OTHER SHOP"          # still a purchase: same checksum
    for t in c["transactions"][:1]:
        t["description"] = "ATM WITHDRAWAL"           # now a non-purchase: different checksum
    assert input_checksum(a) == input_checksum(b)
    assert input_checksum(a) != input_checksum(c)
