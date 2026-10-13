"""Side-by-side comparison of two configurations on the same scenario input (computed here, not in the API)."""

import copy
from decimal import localcontext

from .market import DataError
from .money import CONTEXT, display_money
from .scenario import error_result, parse_scenario, result_dict
from .simulate import simulate


def _run(s: dict, series: str):
    market, rows, cfg = parse_scenario(s)
    try:
        r = simulate(market, rows, cfg)
    except DataError as e:
        return None, error_result(e.code)
    return r, result_dict(r, cfg, series)


def compare_scenarios(base: dict, a: dict, b: dict, series: str = "daily") -> dict:
    """Run `base` with config overrides `a` and `b` (e.g. strategy, reinvest). Difference is b - a."""
    runs = []
    for override in (a, b):
        s = copy.deepcopy(base)
        s["config"].update(override)
        runs.append(_run(s, series))
    (ra, da), (rb, db) = runs
    difference = None
    if ra is not None and rb is not None:
        with localcontext(CONTEXT):
            difference = {
                "ending_value": display_money(rb.ending_value - ra.ending_value),
                "gain": display_money(rb.gain - ra.gain),
                "dividends_earned": display_money(rb.dividends_earned - ra.dividends_earned),
                "uninvested_cash": display_money(rb.uninvested_cash - ra.uninvested_cash),
                "roundup_buys": str(sum(x.kind == "roundup" for x in rb.buys) - sum(x.kind == "roundup" for x in ra.buys)),
                "dividend_buys": str(sum(x.kind == "dividend" for x in rb.buys)
                                     - sum(x.kind == "dividend" for x in ra.buys)),
            }
    return {"a": da, "b": db, "difference": difference}
