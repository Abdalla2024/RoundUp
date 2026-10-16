"""The 'Sideways' scenario wanders in a range and ends near where it started (OQ-15, owner decision 2026-10-16).

Level = what one share held from the first day is worth (the close times the split ratios so far; dividends are not added back).
Bands (SCENARIO-MODEL.md, "Sideways: the stated band"): final level within 15% of the start; the whole path between 0.75x and 1.30x
of the start; largest peak-to-trough fall (maximum drawdown) at most 30%. They hold for the published seed AND for 60 other seeds,
so they come from the model, not from a lucky seed.
"""
from decimal import Decimal

import pytest

from roundup_scenarios import FAMILIES, MODEL_VERSION, STYLES, generate_series, get_published, published_scenarios

FINAL_BAND = Decimal("0.15")
PATH_LOW, PATH_HIGH = Decimal("0.75"), Decimal("1.30")
MAX_DRAWDOWN = Decimal("0.30")


def levels(s):
    m, out, factor = s.market, [], Decimal(1)
    splits = sorted(m.splits, key=lambda x: x.ex_date)
    si = 0
    for d in m.calendar:
        while si < len(splits) and splits[si].ex_date <= d:
            factor *= splits[si].ratio
            si += 1
        out.append(m.closes[d] * factor)
    first = out[0]
    return [x / first for x in out]


def band_problems(s):
    lv = levels(s)
    peak, dd = lv[0], Decimal(0)
    for x in lv:
        peak = max(peak, x)
        dd = max(dd, (peak - x) / peak)
    bad = []
    if abs(lv[-1] - 1) > FINAL_BAND:
        bad.append(f"final level {float(lv[-1]):.3f} is not within {FINAL_BAND} of the start")
    if min(lv) < PATH_LOW or max(lv) > PATH_HIGH:
        bad.append(f"path leaves [{PATH_LOW}, {PATH_HIGH}]: {float(min(lv)):.3f} to {float(max(lv)):.3f}")
    if dd > MAX_DRAWDOWN:
        bad.append(f"maximum drawdown {float(dd):.3f} is above {MAX_DRAWDOWN}")
    return bad


@pytest.mark.parametrize("style", sorted(STYLES))
def test_published_sideways_stays_in_its_band(style):
    assert band_problems(get_published("sideways", style)) == []


@pytest.mark.parametrize("style", sorted(STYLES))
def test_the_band_comes_from_the_model_not_the_seed(style):
    failures = {seed: band_problems(generate_series("sideways", style, seed)) for seed in range(1, 61)}
    assert {k: v for k, v in failures.items() if v} == {}


def test_model_version_changed_and_documented_parameters():
    assert MODEL_VERSION == "scenario-model-2"
    for style in STYLES:
        p = get_published("sideways", style).meta["parameters"]
        assert p["reversion_permille"] == 12 and p["regimes"] == [{"from": "0", "drift_bp": 0, "vol_bp": 70}]
    for fid in FAMILIES:
        if fid != "sideways":
            assert get_published(fid, "broad").meta["parameters"]["reversion_permille"] == 0


# Every other published series must be byte-for-byte what it was under scenario-model-1 (only Sideways changed).
UNCHANGED = {
    ("steady-growth", "broad"): "81344ab2110d41752ecce820f37097b45cd9da8d68db421e20fb5e4c1ec9b9b7",
    ("steady-growth", "dividend"): "acd39b59b87093a587996a61ba1a3032be8d05fc7773d44ce1c65f907cc46975",
    ("crash-and-recovery", "broad"): "b1c96edd103ce9744901538b07321256bfb46e47eed041728417f954ec23cc70",
    ("crash-and-recovery", "dividend"): "7e7d387af4c48b496b14c426d52fc5b2d0ed7ce07257437e85de23f29ffb5795",
    ("high-volatility", "broad"): "14796fde7ea4dad4353777b8801b7f47e1f112725c0dd2cc885cf58f63628ef5",
    ("high-volatility", "dividend"): "aaead661602a8a463ee1ed39fd88ebf36efae3c440761357e547458f74a2547a",
}


@pytest.mark.parametrize("key", sorted(UNCHANGED))
def test_other_scenarios_are_unchanged(key):
    assert get_published(*key).market.checksum() == UNCHANGED[key]


def test_sideways_is_not_one_of_the_unchanged_series():
    old = {"broad": "d75dc665cb7ae5ed684035927c992073638bd34324212f8e7adb840bd04b73f6",
           "dividend": "3c05267913f65cbd8bc630dc8aeb22d3ec8757cc760e85317aa706bac514b010"}
    for style, c in old.items():
        assert get_published("sideways", style).market.checksum() != c


# The independent implementation (written from the spec alone) must agree with the engine on the NEW Sideways series too.
import importlib.util  # noqa: E402
import pathlib  # noqa: E402

from builders import typical_scenario  # noqa: E402
from roundup_engine import run_scenario  # noqa: E402
from roundup_scenarios import market_dict  # noqa: E402

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("crosscheck", _ROOT / "crosscheck" / "crosscheck.py")
_cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cc)


@pytest.mark.parametrize("style", sorted(STYLES))
@pytest.mark.parametrize("strategy", ["threshold", "next_session", "weekly", "monthly"])
@pytest.mark.parametrize("reinvest", [True, False])
def test_engine_and_crosscheck_agree_on_published_sideways(style, strategy, reinvest):
    m = market_dict(get_published("sideways", style))
    s = typical_scenario(f"sideways-{style}", m["calendar"], m["closes"], 10, "0.50", strategy, "2015-01-02", "2024-12-31",
                         reinvest, m["dividends"], m["splits"])
    a, b = run_scenario(s), _cc.run(s)
    strip = lambda d: {k: v for k, v in d.items() if k != "engine_version"}  # noqa: E731
    assert strip(a) == strip(b)
