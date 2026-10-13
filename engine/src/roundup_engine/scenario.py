"""Scenario JSON (fixtures/FORMAT.md) in, result JSON out."""

import hashlib
import json
from datetime import date

from . import ENGINE_VERSION
from .market import DataError, Dividend, MarketSeries, Split
from .money import display_money, display_pct, display_shares, parse_decimal
from .simulate import Config, simulate
from .transactions import is_non_purchase


def _d(s: str) -> date:
    return date.fromisoformat(s)


def parse_scenario(s: dict):
    mk = s["market"]
    market = MarketSeries(
        symbol=mk.get("symbol", ""),
        calendar=tuple(sorted(_d(x) for x in mk["calendar"])),
        closes={_d(k): parse_decimal(v) for k, v in mk["closes"].items()},
        dividends=tuple(Dividend(_d(x["ex_date"]), _d(x["pay_date"]) if x.get("pay_date") else None,
                                 parse_decimal(x["amount_raw"])) for x in mk.get("dividends", [])),
        splits=tuple(Split(_d(x["ex_date"]), parse_decimal(x["ratio"])) for x in mk.get("splits", [])),
        kind=mk.get("kind", "sample"),
    )
    c = s["config"]
    if c.get("reinvest", "true") not in ("true", "false"):
        raise ValueError("reinvest must be 'true' or 'false'")
    cfg = Config(strategy=c["strategy"], start=_d(c["start"]), end=_d(c["end"]),
                 reinvest=c.get("reinvest", "true") == "true")
    return market, list(s.get("transactions", [])), cfg


def _b(x: bool) -> str:
    return "true" if x else "false"


def input_checksum(s: dict) -> str:
    """SHA-256 of the canonical scenario input: market checksum + transactions + config (R-12.4)."""
    market, rows, _ = parse_scenario(s)
    # Each row contributes its resolved category instead of its description and type, so merchant text never
    # feeds a stored hash (D-8) while classification changes still change the checksum.
    canonical = [{"posted_date": r.get("posted_date"), "amount": r.get("amount"), "direction": r.get("direction"),
                  "status": r.get("status"),
                  "category": r.get("category") or ("non_purchase" if is_non_purchase(r.get("type") or "",
                                                                                      r.get("description") or "")
                                                    else "purchase")} for r in rows]
    payload = {"market": market.checksum(), "transactions": canonical, "config": s["config"]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def error_result(code: str) -> dict:
    return {"status": "error", "error_code": code, "summary": None, "buys": None, "series": None,
            "transactions_used": None, "transactions_ignored": None, "engine_version": ENGINE_VERSION}


def run_scenario(s: dict) -> dict:
    market, rows, cfg = parse_scenario(s)
    try:
        r = simulate(market, rows, cfg)
    except DataError as e:
        return error_result(e.code)
    return result_dict(r)


def result_dict(r) -> dict:
    pct = r.gain_pct
    return {
        "status": "ok",
        "error_code": None,
        "summary": {
            "contributed": f"{r.contributed_cents // 100}.{r.contributed_cents % 100:02d}",
            "roundup_buys": str(sum(1 for b in r.buys if b.kind == "roundup")),
            "dividend_buys": str(sum(1 for b in r.buys if b.kind == "dividend")),
            "dividends_earned": display_money(r.dividends_earned),
            "dividends_paid": display_money(r.dividends_paid),
            "shares": display_shares(r.shares),
            "holdings_value": display_money(r.holdings_value),
            "uninvested_cash": display_money(r.uninvested_cash),
            "receivables": display_money(r.receivables),
            "ending_value": display_money(r.ending_value),
            "gain": display_money(r.gain),
            "gain_pct": "n/a" if pct is None else display_pct(pct),
            "as_of": r.as_of.isoformat(),
        },
        "buys": [{"date": b.date.isoformat(), "kind": b.kind, "cash": display_money(b.cash),
                  "price": str(b.price), "shares": display_shares(b.shares),
                  "delayed_by_data_gap": _b(b.delayed_by_data_gap)} for b in r.buys],
        "series": [{"date": p.date.isoformat(), "value": display_money(p.value), "carried": _b(p.carried)}
                   for p in r.series],
        "transactions_used": str(len(r.used)),
        "transactions_ignored": str(len(r.ignored)),
        "engine_version": ENGINE_VERSION,
    }
