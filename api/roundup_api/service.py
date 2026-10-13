"""Glue between validated requests and the engine. No arithmetic here: every number comes from the engine."""

from functools import lru_cache

from roundup_engine import ENGINE_VERSION, run_scenario
from roundup_engine.compare import compare_scenarios
from roundup_engine.generator import generate_transactions
from roundup_engine.scenario import input_checksum
from roundup_scenarios import FAMILIES, LABEL, MODEL_VERSION, STYLES, get_published, market_dict

from .errors import ENGINE_MESSAGES, ApiError


@lru_cache(maxsize=16)
def _market(scenario_id: str, style: str) -> tuple[dict, dict]:
    s = get_published(scenario_id, style)
    return market_dict(s), s.meta


@lru_cache(maxsize=16)
def market_checksum(scenario_id: str, style: str) -> str:
    return get_published(scenario_id, style).market.checksum()


def resolve(scenario_id: str, style: str):
    if scenario_id not in FAMILIES or style not in STYLES:
        raise ApiError(404, "UNKNOWN_SCENARIO", "That scenario or style does not exist. "
                       "See /v1/scenarios for the available ones.")
    market, meta = _market(scenario_id, style)
    return market, meta


def engine_input(req, strategy: str = "threshold", reinvest: bool = True) -> tuple[dict, dict]:
    market, meta = resolve(req.scenario_id, req.style)
    if req.transactions is not None:
        txs = [{"posted_date": t.posted_date, "amount": t.amount, "direction": t.direction, "status": t.status,
                "type": "", "description": t.description or "", **({"category": t.category} if t.category else {})}
               for t in req.transactions]
    elif meta["start"] <= req.start <= req.end <= meta["end"]:
        txs = generate_transactions(seed=req.generate.seed, start=req.start, end=req.end,
                                    max_per_day=req.generate.max_per_day)
    else:
        # The window is outside the scenario's data, so the engine will refuse it (R-12.1, 422 WINDOW_OUTSIDE_DATA).
        # Do not step through every day of an impossible window first: end=9999-12-31 took 8-10 s and then crashed
        # on a date overflow (found by the stage-6 attack test on the deployed preview).
        txs = []
    scenario = {"id": "api", "market": market, "transactions": txs,
                "config": {"strategy": strategy, "start": req.start, "end": req.end,
                           "reinvest": "true" if reinvest else "false"}}
    return scenario, meta


def build_meta(scenario: dict, meta: dict) -> dict:
    return {"engine_version": ENGINE_VERSION, "model_version": MODEL_VERSION, "scenario_id": meta["scenario_id"],
            "style": meta["style"], "scenario_seed": meta["seed"],
            "market_checksum": market_checksum(meta["scenario_id"], meta["style"]),
            "input_checksum": input_checksum(scenario), "label": LABEL}


def _raise_engine_error(result: dict, meta: dict) -> None:
    code = result["error_code"]
    msg = ENGINE_MESSAGES.get(code, "The simulation could not be run on this data.")
    raise ApiError(422, code, msg.format(start=meta["start"], end=meta["end"]))


def simulate(req) -> dict:
    scenario, meta = engine_input(req, req.strategy, req.reinvest)
    result = run_scenario(scenario, series="auto", include_buys=req.buys == "all")   # thinning is the engine's
    if result["status"] != "ok":
        _raise_engine_error(result, meta)
    return {"result": result, "meta": build_meta(scenario, meta)}


def compare(req) -> dict:
    scenario, meta = engine_input(req)
    out = compare_scenarios(scenario,
                            {"strategy": req.a.strategy, "reinvest": "true" if req.a.reinvest else "false"},
                            {"strategy": req.b.strategy, "reinvest": "true" if req.b.reinvest else "false"},
                            series="auto", include_buys=req.buys == "all")
    for side in ("a", "b"):
        if out[side]["status"] != "ok":
            _raise_engine_error(out[side], meta)
    return {**out, "meta": build_meta(scenario, meta)}


def scenarios_listing() -> dict:
    items = []
    for fid, fam in FAMILIES.items():
        styles = []
        for st in STYLES:
            _, meta = _market(fid, st)
            styles.append({"style": st, "name": meta["style_name"], "symbol": meta["symbol"], "start": meta["start"],
                           "end": meta["end"], "market_checksum": market_checksum(fid, st),
                           "parameters": meta["parameters"]})
        items.append({"id": fid, "name": fam["name"], "description": fam["description"], "label": LABEL,
                      "seed": fam["seed"], "styles": styles})
    return {"label": LABEL, "model_version": MODEL_VERSION, "scenarios": items}


SELF_CHECK = {
    "id": "health", "transactions": [{"posted_date": "2024-01-03", "amount": "4.37", "direction": "debit",
                                      "status": "posted", "type": "", "description": ""}],
    "market": {"calendar": ["2024-01-02", "2024-01-03", "2024-01-04"],
               "closes": {"2024-01-02": "50.00", "2024-01-03": "50.00", "2024-01-04": "50.00"},
               "dividends": [], "splits": []},
    "config": {"strategy": "next_session", "start": "2024-01-02", "end": "2024-01-04", "reinvest": "true"},
}


def engine_self_check() -> bool:
    """G-11 in miniature: a $4.37 purchase rounds up 0.63 and buys 0.012600 shares at 50.00."""
    try:
        s = run_scenario(SELF_CHECK)["summary"]
        return s["contributed"] == "0.63" and s["shares"] == "0.012600"
    except Exception:
        return False
