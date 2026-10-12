"""Seeded synthetic market scenarios (SCENARIO-MODEL.md). Integer and Decimal arithmetic only."""

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from functools import lru_cache

from roundup_engine.market import Dividend, MarketSeries, Split
from roundup_engine.money import CONTEXT

from .calendar import trading_calendar

MODEL_VERSION = "scenario-model-1"
LABEL = "Synthetic scenario. Not a real fund, not real prices, and not a forecast."
START, END = date(2012, 1, 3), date(2026, 9, 30)

FAMILIES = {
    "steady-growth": {
        "name": "Steady growth", "seed": 1101, "split_ratio": "3",
        "regimes": [("0", 4, 70)],
        "description": "A synthetic market that rises gradually, with small day-to-day moves.",
    },
    "crash-and-recovery": {
        "name": "Crash and recovery", "seed": 1202, "split_ratio": "0.5",
        "regimes": [("0", 3, 80), ("0.30", -45, 260), ("0.335", 12, 140), ("0.55", 3, 80)],
        "description": "A synthetic market that grows, falls sharply over a few months, then recovers.",
    },
    "sideways": {
        "name": "Sideways", "seed": 1303, "split_ratio": "2",
        "regimes": [("0", 0, 90)],
        "description": "A synthetic market with no overall trend: prices wander up and down.",
    },
    "high-volatility": {
        "name": "High volatility", "seed": 1404, "split_ratio": "2",
        "regimes": [("0", 3, 230)],
        "description": "A synthetic market with large daily swings in both directions.",
    },
}
STYLES = {
    "broad": {"name": "Broad-market style (synthetic)", "start_price": "100.0000", "yield_bp": 150, "drift_adj": 0},
    "dividend": {"name": "Dividend style (synthetic)", "start_price": "40.0000", "yield_bp": 350, "drift_adj": -1},
}

Q4 = Decimal("0.0001")
FLOOR = Decimal("0.0100")


@dataclass(frozen=True)
class ScenarioSeries:
    market: MarketSeries
    meta: dict


def _div_half_even(n: int, d: int) -> int:
    q, r = divmod(n, d)
    if 2 * r > d or (2 * r == d and q % 2):
        q += 1
    return q


def _ex_dates(cal: list[date]) -> list[date]:
    out = []
    for y in range(cal[0].year, cal[-1].year + 1):
        for mth in (3, 6, 9, 12):
            target = date(y, mth, 15)
            nxt = next((d for d in cal if d >= target), None)
            if nxt is not None and (not out or nxt != out[-1]):
                out.append(nxt)
    return out


def generate_series(family: str, style: str, seed: int, start: date = START, end: date = END) -> ScenarioSeries:
    fam, sty = FAMILIES[family], STYLES[style]
    rng = random.Random(f"{family}:{style}:{seed}")
    cal = trading_calendar(start, end)
    n = len(cal)
    ex_dates = set(_ex_dates(cal))

    while True:                                   # split day: 40-60% through, away from dividends
        i = rng.randint(n * 40 // 100, n * 60 // 100)
        if cal[i] not in ex_dates and cal[i + 1] not in ex_dates:
            split_day = cal[i]
            break
    ratio = Decimal(fam["split_ratio"])
    regimes = [(int(Decimal(f) * n), drift, vol) for f, drift, vol in fam["regimes"]]

    closes, dividends = {}, []
    with localcontext(CONTEXT):
        prev = Decimal(sty["start_price"])
        for t, d in enumerate(cal):
            if t == 0:
                closes[d] = prev
                continue
            _, drift, vol = [rg for rg in regimes if rg[0] <= t][-1]
            z = sum(rng.randint(0, 1000) for _ in range(12)) - 6000
            r = drift + sty["drift_adj"] + _div_half_even(vol * z, 1000)
            cap = 500 if d == split_day else 2500
            r = max(-cap, min(cap, r))
            close = prev * (10000 + r) / 10000
            if d in ex_dates:
                amount = max((prev * sty["yield_bp"] / 40000).quantize(Q4, rounding=ROUND_HALF_EVEN), Q4)
                close -= amount
                dividends.append(Dividend(d, d + timedelta(days=7), amount))
            if d == split_day:
                close = close / ratio
            close = max(close.quantize(Q4, rounding=ROUND_HALF_EVEN), FLOOR)
            closes[d] = close
            prev = close

    symbol = f"SYN-{family.upper()}-{style.upper()}"
    market = MarketSeries(symbol=symbol, calendar=tuple(cal), closes=closes, dividends=tuple(dividends),
                          splits=(Split(split_day, ratio),), kind="sample")
    meta = {
        "scenario_id": family, "name": fam["name"], "description": fam["description"], "style": style,
        "style_name": sty["name"], "label": LABEL, "seed": seed, "model_version": MODEL_VERSION,
        "symbol": symbol, "start": cal[0].isoformat(), "end": cal[-1].isoformat(),
        "parameters": {"regimes": [{"from": f, "drift_bp": dr, "vol_bp": v} for f, dr, v in fam["regimes"]],
                       "split_ratio": fam["split_ratio"], "start_price": sty["start_price"],
                       "yield_bp": sty["yield_bp"], "drift_adj_bp": sty["drift_adj"]},
    }
    return ScenarioSeries(market, meta)


def market_dict(s: ScenarioSeries) -> dict:
    """The series in fixtures/FORMAT.md shape (all numbers as strings)."""
    m = s.market
    return {
        "symbol": m.symbol, "kind": m.kind,
        "calendar": [d.isoformat() for d in m.calendar],
        "closes": {d.isoformat(): format(v, "f") for d, v in m.closes.items()},
        "dividends": [{"ex_date": x.ex_date.isoformat(), "pay_date": x.pay_date.isoformat(),
                       "amount_raw": format(x.amount, "f")} for x in m.dividends],
        "splits": [{"ex_date": x.ex_date.isoformat(), "ratio": format(x.ratio, "f")} for x in m.splits],
    }


@lru_cache(maxsize=1)
def _published() -> tuple[ScenarioSeries, ...]:
    return tuple(generate_series(f, s, FAMILIES[f]["seed"]) for f in FAMILIES for s in STYLES)


def published_scenarios() -> list[ScenarioSeries]:
    return list(_published())


def get_published(scenario_id: str, style: str) -> ScenarioSeries:
    for s in _published():
        if s.meta["scenario_id"] == scenario_id and s.meta["style"] == style:
            return s
    raise KeyError((scenario_id, style))
