"""Contract tests (API.md), plus: API results must equal direct engine results."""

import copy

from conftest import base_body

from roundup_engine import ENGINE_VERSION, run_scenario
from roundup_engine.compare import compare_scenarios
from roundup_engine.generator import generate_transactions
from roundup_engine.scenario import input_checksum
from roundup_scenarios import FAMILIES, LABEL, MODEL_VERSION, get_published, market_dict


def engine_scenario(body):
    """Build the engine input independently of the API, from the request body."""
    if "transactions" in body:
        txs = [{"posted_date": t["posted_date"], "amount": t["amount"], "direction": t["direction"],
                "status": t.get("status", "posted"), "type": "", "description": t.get("description", ""),
                **({"category": t["category"]} if "category" in t else {})} for t in body["transactions"]]
    else:
        g = body["generate"]
        txs = generate_transactions(seed=g["seed"], start=body["start"], end=body["end"], max_per_day=g["max_per_day"])
    return {"id": "api", "market": market_dict(get_published(body["scenario_id"], body["style"])),
            "transactions": txs,
            "config": {"strategy": body.get("strategy", "threshold"), "start": body["start"], "end": body["end"],
                       "reinvest": "true" if body.get("reinvest", True) else "false"}}


def test_health(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "engine_version": ENGINE_VERSION, "model_version": MODEL_VERSION,
                        "scenarios": 4}
    assert r.headers["X-Request-ID"]


def test_scenarios_list(client):
    r = client.get("/v1/scenarios").json()
    assert r["label"] == LABEL and r["model_version"] == MODEL_VERSION
    assert {s["id"] for s in r["scenarios"]} == set(FAMILIES)
    for s in r["scenarios"]:
        assert s["seed"] == FAMILIES[s["id"]]["seed"] and s["label"] == LABEL
        assert {x["style"] for x in s["styles"]} == {"broad", "dividend"}
        for st in s["styles"]:
            assert st["market_checksum"] == get_published(s["id"], st["style"]).market.checksum()
            assert st["symbol"].startswith("SYN-")


def test_assumptions(client):
    r = client.get("/v1/assumptions").json()
    ids = {a["id"] for a in r["assumptions"]}
    assert {"R-2.2", "R-5.1", "R-5.2", "R-7.1", "R-8.5", "R-10.1", "R-10.4", "R-11.3", "R-12.5"} <= ids
    assert "not a forecast" in r["disclaimer"].lower() or "past performance" in r["disclaimer"].lower()


def test_simulate_equals_engine(client):
    body = base_body(strategy="next_session")
    r = client.post("/v1/simulate", json=body)
    assert r.status_code == 200, r.text
    out = r.json()
    s = engine_scenario(body)
    assert out["result"] == run_scenario(s, series="auto")
    m = out["meta"]
    assert m == {"engine_version": ENGINE_VERSION, "model_version": MODEL_VERSION, "scenario_id": "steady-growth",
                 "style": "broad", "scenario_seed": 1101,
                 "market_checksum": get_published("steady-growth", "broad").market.checksum(),
                 "input_checksum": input_checksum(s), "label": LABEL}
    assert out["result"]["summary"]["contributed"] == "1.53"   # 0.63 + 0.90; the card payment is excluded


def test_simulate_generate_equals_engine(client):
    body = base_body(start="2012-01-03", end="2026-09-30", strategy="weekly", reinvest=False,
                     scenario_id="crash-and-recovery", style="dividend")
    del body["transactions"]
    body["generate"] = {"seed": 7, "max_per_day": 2}
    out = client.post("/v1/simulate", json=body).json()
    assert out["result"] == run_scenario(engine_scenario(body), series="auto")
    assert out["result"]["series_resolution"] == "weekly"          # 2012-2026: thinned for the chart
    assert int(out["result"]["summary"]["roundup_buys"]) > 100


def test_simulate_deterministic(client):
    a = client.post("/v1/simulate", json=base_body()).json()
    b = client.post("/v1/simulate", json=base_body()).json()
    assert a == b


def test_compare_equals_engine(client):
    body = base_body(a={"strategy": "next_session", "reinvest": True}, b={"strategy": "monthly", "reinvest": False})
    for k in ("strategy", "reinvest"):
        body.pop(k)
    r = client.post("/v1/compare", json=body)
    assert r.status_code == 200, r.text
    out = r.json()
    s = engine_scenario(body)
    expected = compare_scenarios(s, {"strategy": "next_session", "reinvest": "true"},
                                 {"strategy": "monthly", "reinvest": "false"}, series="auto")
    assert out["a"] == expected["a"] and out["b"] == expected["b"] and out["difference"] == expected["difference"]
    assert out["meta"]["input_checksum"] == input_checksum(s)


def test_window_outside_data_plain_message(client):
    r = client.post("/v1/simulate", json=base_body(start="2011-06-01"))
    assert r.status_code == 422
    e = r.json()["error"]
    assert e["code"] == "WINDOW_OUTSIDE_DATA" and "2012-01-03" in e["message"]


def test_unknown_scenario(client):
    for kw in ({"scenario_id": "nope"}, {"style": "growth"}, {"scenario_id": "../etc/passwd"}):
        r = client.post("/v1/simulate", json=base_body(**kw))
        assert r.status_code in (404, 422)
        assert r.json()["error"]["code"] in ("UNKNOWN_SCENARIO", "INVALID_INPUT")


CSV = ("Date,Amount,Description\n"
       "2015-01-05,4.37,COFFEE SHOP\n"
       "2015-01-06,-20.00,REFUND\n"
       "2015-01-07,512.37,PAYMENT TO CHASE CARD\n"
       "2015-01-08,4.375,BAD\n")


def test_parse_basic_no_descriptions_echoed(client):
    r = client.post("/v1/transactions/parse", json={
        "csv": CSV, "mapping": {"date": "Date", "amount": "Amount", "description": "Description"},
        "sign_convention": "debits_positive"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["columns"] == ["Date", "Amount", "Description"]
    assert out["date_column_used"] == "Date" and out["sign_convention"] == "debits_positive"
    t = out["transactions"]
    assert [x["row"] for x in t] == [2, 3, 4, 5]
    assert t[0] == {"row": 2, "posted_date": "2015-01-05", "amount": "4.37", "direction": "debit",
                    "status": "posted", "category": "purchase", "problem": None}
    assert t[1]["direction"] == "credit" and t[2]["category"] == "non_purchase"
    assert t[3]["problem"] == "invalid_amount"
    assert out["summary"]["problems"]["invalid_amount"] == 1 and out["summary"]["non_purchases"] == 1
    for word in ("COFFEE", "REFUND", "CHASE", "BAD"):
        assert word not in r.text


def test_parse_then_simulate_round_trip(client):
    parsed = client.post("/v1/transactions/parse", json={
        "csv": CSV, "mapping": {"date": "Date", "amount": "Amount", "description": "Description"},
        "sign_convention": "debits_positive"}).json()["transactions"]
    txs = [{k: x[k] for k in ("posted_date", "amount", "direction", "status", "category")}
           for x in parsed if x["problem"] is None]
    r = client.post("/v1/simulate", json=base_body(transactions=txs))
    assert r.status_code == 200, r.text
    assert r.json()["result"]["summary"]["contributed"] == "0.63"


def test_parse_sign_convention_required_and_inferred(client):
    r = client.post("/v1/transactions/parse", json={"csv": CSV, "mapping": {"date": "Date", "amount": "Amount"}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "SIGN_CONVENTION_REQUIRED"
    csv2 = "Date,Debit,Credit\n2015-01-05,4.37,\n2015-01-06,,20.00\n"
    r = client.post("/v1/transactions/parse", json={"csv": csv2, "mapping": {"date": "Date", "debit": "Debit",
                                                                            "credit": "Credit"}})
    assert r.status_code == 200 and r.json()["sign_convention"] == "separate_columns"


def test_parse_neutralises_formula_headers(client):
    csv = "=cmd|' /C calc'!A0,+Amount,@Desc,\tX,－Y\n2015-01-05,4.37,a,b,c\n"
    r = client.post("/v1/transactions/parse", json={"csv": csv, "mapping": {"date": "=cmd|' /C calc'!A0",
                                                                           "amount": "+Amount"},
                                                   "sign_convention": "debits_positive"})
    assert r.status_code == 200, r.text
    cols = r.json()["columns"]
    # column names are trimmed, so a leading tab is removed (harmless) rather than quoted
    assert cols == ["'=cmd|' /C calc'!A0", "'+Amount", "'@Desc", "X", "'－Y"]


def test_parse_missing_mapped_column(client):
    r = client.post("/v1/transactions/parse", json={"csv": CSV, "mapping": {"date": "When", "amount": "Amount"},
                                                   "sign_convention": "debits_positive"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "CSV_INVALID"


def test_parse_explicit_convention_must_fit_mapping(client):
    """Independent tester's ambiguity #17: a convention that contradicts the mapping is refused, not silently
    turned into a file of invalid rows."""
    csv2 = "Date,Debit,Credit\n2015-01-05,4.37,\n"
    for conv, mapping in [("debits_positive", {"date": "Date", "debit": "Debit", "credit": "Credit"}),
                          ("separate_columns", {"date": "Date", "debit": "Debit"}),
                          ("type_column", {"date": "Date", "debit": "Debit", "credit": "Credit"})]:
        r = client.post("/v1/transactions/parse", json={"csv": csv2, "mapping": mapping, "sign_convention": conv})
        assert r.status_code == 422 and r.json()["error"]["fields"] == ["sign_convention"], conv


def test_parse_missing_column_not_echoed(client):
    r = client.post("/v1/transactions/parse", json={"csv": CSV, "mapping": {"date": "=HYPERLINK(1)", "amount": "Amount"},
                                                   "sign_convention": "debits_positive"})
    assert r.status_code == 422 and r.json()["error"]["fields"] == ["mapping.date"]
    assert "HYPERLINK" not in r.text


def test_parse_strips_utf8_bom(client):
    r = client.post("/v1/transactions/parse", json={"csv": "﻿" + CSV, "mapping": {"date": "Date", "amount": "Amount"},
                                                   "sign_convention": "debits_positive"})
    assert r.status_code == 200 and r.json()["columns"][0] == "Date"


def test_buys_none_option_equals_engine(client):
    body = base_body(start="2012-01-03", end="2026-09-30", buys="none")
    del body["transactions"]
    body["generate"] = {"seed": 3, "max_per_day": 2}
    out = client.post("/v1/simulate", json=body).json()
    eng = run_scenario(engine_scenario(body), series="auto", include_buys=False)
    assert out["result"] == eng and out["result"]["buys"] == [] and out["result"]["buys_included"] is False
    assert out["result"]["summary"]["deepest_dip"] is None or set(out["result"]["summary"]["deepest_dip"]) == \
        {"date", "value", "added", "below_by"}


def test_buys_option_validated(client):
    assert client.post("/v1/simulate", json=base_body(buys="some")).status_code == 422


def test_cors_allows_only_the_configured_origin(make_client):
    c = make_client(allowed_origin="https://roundup-web.vercel.app")
    pre = c.options("/v1/simulate", headers={"Origin": "https://roundup-web.vercel.app",
                                              "Access-Control-Request-Method": "POST",
                                              "Access-Control-Request-Headers": "content-type,authorization"})
    assert pre.status_code == 200
    assert pre.headers["access-control-allow-origin"] == "https://roundup-web.vercel.app"
    assert "authorization" in pre.headers["access-control-allow-headers"].lower()
    ok = c.post("/v1/simulate", json=base_body(), headers={"Origin": "https://roundup-web.vercel.app"})
    assert ok.headers["access-control-allow-origin"] == "https://roundup-web.vercel.app"
    bad = c.post("/v1/simulate", json=base_body(), headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
    bad_pre = c.options("/v1/simulate", headers={"Origin": "https://evil.example",
                                                 "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad_pre.headers
    assert "access-control-allow-credentials" not in ok.headers          # tokens go in a header, not cookies


def test_no_cors_without_configuration(client):
    r = client.post("/v1/simulate", json=base_body(), headers={"Origin": "https://roundup-web.vercel.app"})
    assert "access-control-allow-origin" not in r.headers
