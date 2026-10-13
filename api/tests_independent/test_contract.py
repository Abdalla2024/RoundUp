"""Contract tests for the RoundUp API v1, written only from API.md."""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apisupport import (
    AMOUNT_RE, CENTS_RE, DESC_MARKER, DROP, HEX64, LABEL_TEXT, MAPPING_KEYS, PUBLISHABLE_KEY,
    SCRIPT_MARKER, STRATEGIES, STYLES, SUPABASE_URL, UUID_RE, FakeStorage, Run, assert_error,
    claims, compare_body, default_run, find_key, listing, make_app, make_client, make_txs,
    mapping, parse_body, post_raw, saved_body, sign, sim_body, window_for,
)

META_KEYS = {"engine_version", "model_version", "scenario_id", "style", "scenario_seed",
             "market_checksum", "input_checksum", "label"}
DIFF_KEYS = ("ending_value", "gain", "dividends_earned", "uninvested_cash", "roundup_buys",
             "dividend_buys")
REQUIRED_ASSUMPTIONS = ("R-2.1", "R-2.2", "R-5.1", "R-5.2", "R-7.1", "R-8.5", "R-10.1",
                        "R-10.4", "R-11.3", "R-12.5")


def check_meta(meta: dict, run: Run):
    assert META_KEYS <= set(meta), META_KEYS - set(meta)
    assert meta["scenario_id"] == run.scenario_id
    assert meta["style"] == run.style_name
    assert isinstance(meta["scenario_seed"], int) and not isinstance(meta["scenario_seed"], bool)
    assert meta["scenario_seed"] == run.scenario["seed"]
    assert HEX64.match(meta["market_checksum"]), meta["market_checksum"]
    assert HEX64.match(meta["input_checksum"]), meta["input_checksum"]
    assert meta["market_checksum"] == run.style["market_checksum"]
    assert isinstance(meta["engine_version"], str) and meta["engine_version"]
    assert isinstance(meta["model_version"], str) and meta["model_version"]
    assert meta["label"] == LABEL_TEXT


def check_result(result: dict, meta: dict | None = None):
    assert isinstance(result, dict)
    for k in ("status", "summary", "buys", "series", "engine_version"):
        assert k in result, f"engine result missing {k}"
    if meta is not None:
        assert result["engine_version"] == meta["engine_version"]


# ================================================================ general

def test_every_response_has_fresh_request_id(client):
    r1 = client.get("/v1/health", headers={"X-Request-ID": "client-chosen-id"})
    r2 = client.get("/v1/health", headers={"X-Request-ID": "client-chosen-id"})
    for r in (r1, r2):
        rid = r.headers.get("x-request-id")
        assert rid and rid != "client-chosen-id"
    assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


def test_request_id_on_error_responses(client):
    for r in (client.get("/v1/does-not-exist"), client.get("/v1/simulate"),
              post_raw(client, "/v1/simulate", "{")):
        assert r.headers.get("x-request-id")


def test_unknown_path_is_404_not_found(client):
    assert_error(client.get("/v1/nope"), 404, "NOT_FOUND")
    assert_error(client.post("/v1/nope", json={}), 404, "NOT_FOUND")
    assert_error(client.get("/simulate"), 404, "NOT_FOUND")


@pytest.mark.parametrize("method,path", [
    ("GET", "/v1/simulate"), ("GET", "/v1/compare"), ("GET", "/v1/transactions/parse"),
    ("GET", "/v1/saved"), ("POST", "/v1/health"), ("POST", "/v1/scenarios"),
    ("DELETE", "/v1/scenarios"), ("PUT", "/v1/simulate"), ("POST", "/v1/assumptions"),
])
def test_wrong_method_is_405(client, method, path):
    r = client.request(method, path, json={} if method != "GET" else None)
    assert_error(r, 405, "METHOD_NOT_ALLOWED")


def test_post_without_json_content_type_is_415(client, run):
    body = json.dumps(sim_body(run))
    assert_error(post_raw(client, "/v1/simulate", body, content_type=None), 415, "UNSUPPORTED_MEDIA_TYPE")
    assert_error(post_raw(client, "/v1/simulate", body, content_type="text/plain"), 415,
                 "UNSUPPORTED_MEDIA_TYPE")


def test_invalid_json_is_400(client):
    assert_error(post_raw(client, "/v1/simulate", "{not json"), 400, "INVALID_JSON")
    assert_error(post_raw(client, "/v1/simulate", "[]"), 400, "INVALID_JSON")


# ================================================================ health

def test_health(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    b = r.json()
    assert b["status"] == "ok"
    assert b["scenarios"] == 4
    assert isinstance(b["engine_version"], str) and b["engine_version"]
    assert isinstance(b["model_version"], str) and b["model_version"]


def test_health_versions_match_scenarios_and_meta(client, run):
    h = client.get("/v1/health").json()
    lst = listing(client)
    assert lst["model_version"] == h["model_version"]
    r = client.post("/v1/simulate", json=sim_body(run))
    assert r.status_code == 200, r.text
    meta = r.json()["meta"]
    assert meta["engine_version"] == h["engine_version"]
    assert meta["model_version"] == h["model_version"]


# ================================================================ scenarios

def test_scenarios_listing_shape(client):
    b = listing(client)
    assert isinstance(b["label"], str) and b["label"]
    assert isinstance(b["model_version"], str) and b["model_version"]
    scs = b["scenarios"]
    assert len(scs) == 4
    ids = [s["id"] for s in scs]
    assert len(set(ids)) == 4
    for s in scs:
        for k in ("id", "name", "description", "label", "seed", "styles"):
            assert k in s, k
        assert isinstance(s["seed"], int) and not isinstance(s["seed"], bool)
        assert sorted(x["style"] for x in s["styles"]) == sorted(STYLES)
        for st in s["styles"]:
            for k in ("style", "name", "symbol", "start", "end", "market_checksum", "parameters"):
                assert k in st, k
            assert st["symbol"].startswith("SYN-")
            assert HEX64.match(st["market_checksum"])
            assert date.fromisoformat(st["start"]) < date.fromisoformat(st["end"])
            assert isinstance(st["parameters"], dict)
    checksums = [st["market_checksum"] for s in scs for st in s["styles"]]
    assert len(set(checksums)) == 8, "each scenario/style series should be distinct"


def test_scenarios_listing_contains_documented_example(client):
    ids = {s["id"] for s in listing(client)["scenarios"]}
    assert "steady-growth" in ids


def test_scenarios_listing_is_deterministic(client):
    assert client.get("/v1/scenarios").json() == client.get("/v1/scenarios").json()


# ================================================================ assumptions

def test_assumptions(client):
    r = client.get("/v1/assumptions")
    assert r.status_code == 200
    b = r.json()
    assert isinstance(b["disclaimer"], str) and b["disclaimer"].strip()
    items = b["assumptions"]
    assert isinstance(items, list) and items
    for it in items:
        assert {"id", "title", "text"} <= set(it)
        for k in ("id", "title", "text"):
            assert isinstance(it[k], str) and it[k].strip()
    ids = {it["id"] for it in items}
    missing = [i for i in REQUIRED_ASSUMPTIONS if i not in ids]
    assert not missing, f"missing assumptions {missing}"
    # The sample-data label must be present somewhere (as R-12.5 or its own item).
    text = json.dumps(b).lower()
    assert "sample" in text or "synthetic" in text


# ================================================================ simulate

def test_simulate_shape_and_meta(client, run):
    r = client.post("/v1/simulate", json=sim_body(run))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json")
    b = r.json()
    assert set(b) == {"result", "meta"}
    check_meta(b["meta"], run)
    check_result(b["result"], b["meta"])


def test_simulate_is_deterministic(client, run):
    body = sim_body(run)
    r1 = client.post("/v1/simulate", json=body).json()
    r2 = client.post("/v1/simulate", json=body).json()
    assert r1["meta"]["input_checksum"] == r2["meta"]["input_checksum"]
    assert r1["result"] == r2["result"]
    assert r1["meta"] == r2["meta"]


def test_simulate_deterministic_across_app_instances(keys, run):
    body = sim_body(run)
    outs = []
    for _ in range(2):
        with make_client(make_app(keys=keys)) as c:
            outs.append(c.post("/v1/simulate", json=body).json())
    assert outs[0] == outs[1]


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("reinvest", [True, False])
def test_simulate_every_strategy(client, run, strategy, reinvest):
    r = client.post("/v1/simulate", json=sim_body(run, strategy=strategy, reinvest=reinvest))
    assert r.status_code == 200, r.text
    check_meta(r.json()["meta"], run)
    check_result(r.json()["result"])


def test_simulate_every_scenario_and_style(client):
    for sc in listing(client)["scenarios"]:
        for st in sc["styles"]:
            s, e = window_for(st)
            run = Run(sc, st, s, e)
            r = client.post("/v1/simulate", json=sim_body(run))
            assert r.status_code == 200, (sc["id"], st["style"], r.text)
            check_meta(r.json()["meta"], run)


def test_input_checksum_depends_on_input(client, run):
    base = client.post("/v1/simulate", json=sim_body(run)).json()["meta"]["input_checksum"]
    other_strategy = client.post("/v1/simulate", json=sim_body(run, strategy="monthly")).json()
    txs = make_txs(run.start)
    txs[0]["amount"] = "4.38"
    other_tx = client.post("/v1/simulate", json=sim_body(run, txs=txs)).json()
    assert other_strategy["meta"]["input_checksum"] != base
    assert other_tx["meta"]["input_checksum"] != base


def test_input_checksum_ignores_description(client, run):
    """description is used only for classification; an explicit category makes it irrelevant."""
    a = make_txs(run.start, category="purchase", description="COFFEE")
    b = make_txs(run.start, category="purchase", description="TEA")
    ra = client.post("/v1/simulate", json=sim_body(run, txs=a)).json()
    rb = client.post("/v1/simulate", json=sim_body(run, txs=b)).json()
    assert ra["meta"]["input_checksum"] == rb["meta"]["input_checksum"]
    assert ra["result"] == rb["result"]


def test_category_override_is_honoured(client, run):
    txs = make_txs(run.start, category="purchase")
    purchase = client.post("/v1/simulate", json=sim_body(run, txs=txs)).json()
    txs[0]["category"] = "non_purchase"
    non = client.post("/v1/simulate", json=sim_body(run, txs=txs)).json()
    assert purchase["meta"]["input_checksum"] != non["meta"]["input_checksum"]


@pytest.mark.parametrize("extra", [
    {"status": "posted"}, {"status": "pending"}, {"status": "cancelled"},
    {"category": "purchase"},
])
def test_simulate_optional_transaction_fields(client, run, extra):
    r = client.post("/v1/simulate", json=sim_body(run, txs=make_txs(run.start, **extra)))
    assert r.status_code == 200, r.text


def test_simulate_minimal_transaction(client, run):
    txs = [{"posted_date": (run.start + timedelta(days=5)).isoformat(), "amount": "4.37", "direction": "debit"}]
    assert client.post("/v1/simulate", json=sim_body(run, txs=txs)).status_code == 200


@pytest.mark.parametrize("amount", ["0.01", "4", "4.3", "4.37", "9999999", "9999999.99", "0001.50"])
def test_simulate_accepts_amount_grammar(client, run, amount):
    txs = make_txs(run.start, n=1)
    txs[0]["amount"] = amount
    r = client.post("/v1/simulate", json=sim_body(run, txs=txs))
    assert r.status_code == 200, (amount, r.text)


def test_simulate_description_never_echoed(client, run):
    txs = make_txs(run.start, description=DESC_MARKER + SCRIPT_MARKER[:100])
    r = client.post("/v1/simulate", json=sim_body(run, txs=txs))
    assert r.status_code == 200
    assert DESC_MARKER not in r.text
    assert "<script" not in r.text


def test_simulate_description_140_ok_141_rejected(client, run):
    txs = make_txs(run.start, n=1, description="x" * 140)
    assert client.post("/v1/simulate", json=sim_body(run, txs=txs)).status_code == 200
    txs = make_txs(run.start, n=1, description="x" * 141)
    err = assert_error(client.post("/v1/simulate", json=sim_body(run, txs=txs)), 422, "INVALID_INPUT")
    assert "transactions.0.description" in err["fields"]


def test_simulate_generate(client, run):
    body = sim_body(run, generate={"seed": 42, "max_per_day": 2})
    r1 = client.post("/v1/simulate", json=body)
    assert r1.status_code == 200, r1.text
    check_meta(r1.json()["meta"], run)
    r2 = client.post("/v1/simulate", json=body)
    assert r1.json() == r2.json()
    other = client.post("/v1/simulate", json=sim_body(run, generate={"seed": 43, "max_per_day": 2})).json()
    assert other["meta"]["input_checksum"] != r1.json()["meta"]["input_checksum"]


@pytest.mark.parametrize("seed,mpd", [(0, 1), (2147483647, 3), (1, 2)])
def test_simulate_generate_bounds_accepted(client, run, seed, mpd):
    r = client.post("/v1/simulate", json=sim_body(run, generate={"seed": seed, "max_per_day": mpd}))
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("gen,field", [
    ({"seed": -1, "max_per_day": 1}, "generate.seed"),
    ({"seed": 2147483648, "max_per_day": 1}, "generate.seed"),
    ({"seed": 1, "max_per_day": 0}, "generate.max_per_day"),
    ({"seed": 1, "max_per_day": 4}, "generate.max_per_day"),
    ({"max_per_day": 1}, "generate.seed"),
    ({"seed": 1}, "generate.max_per_day"),
])
def test_simulate_generate_out_of_range(client, run, gen, field):
    err = assert_error(client.post("/v1/simulate", json=sim_body(run, generate=gen)), 422, "INVALID_INPUT")
    assert field in err["fields"], err


def test_transactions_and_generate_both_or_neither(client, run):
    both = sim_body(run)
    both["generate"] = {"seed": 1, "max_per_day": 1}
    assert_error(client.post("/v1/simulate", json=both), 422, "INVALID_INPUT")
    neither = sim_body(run)
    del neither["transactions"]
    assert_error(client.post("/v1/simulate", json=neither), 422, "INVALID_INPUT")


def test_empty_transactions_rejected(client, run):
    err = assert_error(client.post("/v1/simulate", json=sim_body(run, txs=[])), 422, "INVALID_INPUT")
    assert "transactions" in err["fields"]


def test_20000_transactions_accepted(client, run):
    txs = [{"posted_date": (run.start + timedelta(days=3 + i % 300)).isoformat(),
            "amount": "1.23", "direction": "debit"} for i in range(20_000)]
    r = client.post("/v1/simulate", json=sim_body(run, txs=txs))
    assert r.status_code == 200, r.text[:500]


@pytest.mark.parametrize("missing", ["scenario_id", "style", "strategy", "reinvest"])
def test_simulate_missing_required_field(client, run, missing):
    body = sim_body(run)
    del body[missing]
    err = assert_error(client.post("/v1/simulate", json=body), 422, "INVALID_INPUT")
    assert missing in err["fields"]


@pytest.mark.parametrize("missing", ["posted_date", "amount", "direction"])
def test_transaction_missing_required_field(client, run, missing):
    txs = make_txs(run.start, n=3)
    del txs[2][missing]
    err = assert_error(client.post("/v1/simulate", json=sim_body(run, txs=txs)), 422, "INVALID_INPUT")
    assert f"transactions.2.{missing}" in err["fields"]


def test_field_path_format_for_bad_amount(client, run):
    txs = make_txs(run.start, n=5)
    txs[3]["amount"] = "4.375"
    err = assert_error(client.post("/v1/simulate", json=sim_body(run, txs=txs)), 422, "INVALID_INPUT")
    assert err["fields"] == ["transactions.3.amount"] or "transactions.3.amount" in err["fields"]


@pytest.mark.parametrize("field,value", [
    ("strategy", "daily"), ("strategy", "THRESHOLD"), ("strategy", ""),
])
def test_bad_strategy(client, run, field, value):
    body = sim_body(run)
    body[field] = value
    err = assert_error(client.post("/v1/simulate", json=body), 422, "INVALID_INPUT")
    assert field in err["fields"]


@pytest.mark.parametrize("field,value", [
    ("direction", "DEBIT"), ("direction", "withdrawal"), ("status", "void"),
    ("status", "Posted"), ("category", "groceries"), ("category", ""),
])
def test_bad_enum_in_transaction(client, run, field, value):
    txs = make_txs(run.start, n=2)
    txs[1][field] = value
    err = assert_error(client.post("/v1/simulate", json=sim_body(run, txs=txs)), 422, "INVALID_INPUT")
    assert f"transactions.1.{field}" in err["fields"]


def test_unknown_scenario_and_style(client, run):
    body = sim_body(run)
    body["scenario_id"] = "no-such-scenario"
    assert_error(client.post("/v1/simulate", json=body), 404, "UNKNOWN_SCENARIO")
    body = sim_body(run)
    body["style"] = "growth"
    assert_error(client.post("/v1/simulate", json=body), 404, "UNKNOWN_SCENARIO")


def test_window_outside_data(client, run):
    before = sim_body(run)
    before["start"] = (date.fromisoformat(run.style["start"]) - timedelta(days=30)).isoformat()
    assert_error(client.post("/v1/simulate", json=before), 422, "WINDOW_OUTSIDE_DATA")
    after = sim_body(run)
    after["end"] = (date.fromisoformat(run.style["end"]) + timedelta(days=30)).isoformat()
    assert_error(client.post("/v1/simulate", json=after), 422, "WINDOW_OUTSIDE_DATA")
    reversed_ = sim_body(run)
    reversed_["start"], reversed_["end"] = reversed_["end"], reversed_["start"]
    assert_error(client.post("/v1/simulate", json=reversed_), 422, "WINDOW_OUTSIDE_DATA")


def test_full_scenario_range_accepted(client, run):
    body = sim_body(run)
    body["start"], body["end"] = run.style["start"], run.style["end"]
    assert client.post("/v1/simulate", json=body).status_code == 200


# ================================================================ compare

def test_compare_shape(client, run):
    r = client.post("/v1/compare", json=compare_body(run))
    assert r.status_code == 200, r.text
    b = r.json()
    assert set(b) == {"a", "b", "difference", "meta"}
    check_meta(b["meta"], run)
    check_result(b["a"], b["meta"])
    check_result(b["b"], b["meta"])
    d = b["difference"]
    for k in DIFF_KEYS:
        assert k in d, f"difference missing {k}"
    for k in ("ending_value", "gain", "dividends_earned", "uninvested_cash"):
        assert isinstance(d[k], str) and CENTS_RE.match(d[k]), (k, d[k])
    for k in ("roundup_buys", "dividend_buys"):
        # EDITED after contract clarification: counts are integer strings, like all engine result values
        assert isinstance(d[k], str) and d[k].lstrip("-").isdigit(), (k, d[k])


def test_compare_matches_two_simulates(client, run):
    body = compare_body(run, a={"strategy": "threshold", "reinvest": True},
                        b={"strategy": "weekly", "reinvest": False})
    cmp_ = client.post("/v1/compare", json=body).json()
    sa = client.post("/v1/simulate", json=sim_body(run, strategy="threshold", reinvest=True)).json()
    sb = client.post("/v1/simulate", json=sim_body(run, strategy="weekly", reinvest=False)).json()
    assert cmp_["a"] == sa["result"]
    assert cmp_["b"] == sb["result"]


def test_compare_identical_runs_have_zero_difference(client, run):
    same = {"strategy": "threshold", "reinvest": True}
    d = client.post("/v1/compare", json=compare_body(run, a=same, b=same)).json()["difference"]
    for k in ("ending_value", "gain", "dividends_earned", "uninvested_cash"):
        assert Decimal(d[k]) == 0
    assert d["roundup_buys"] == "0" and d["dividend_buys"] == "0"  # EDITED: integer strings (contract clarified)


def test_compare_difference_is_b_minus_a(client, run):
    a = {"strategy": "threshold", "reinvest": True}
    b = {"strategy": "monthly", "reinvest": False}
    d1 = client.post("/v1/compare", json=compare_body(run, a=a, b=b)).json()["difference"]
    d2 = client.post("/v1/compare", json=compare_body(run, a=b, b=a)).json()["difference"]
    for k in DIFF_KEYS:
        assert Decimal(str(d1[k])) == -Decimal(str(d2[k])), k


def test_compare_is_deterministic(client, run):
    body = compare_body(run, generate={"seed": 7, "max_per_day": 3})
    assert client.post("/v1/compare", json=body).json() == client.post("/v1/compare", json=body).json()


def test_compare_data_error_propagates(client, run):
    body = compare_body(run)
    body["start"], body["end"] = body["end"], body["start"]
    assert_error(client.post("/v1/compare", json=body), 422, "WINDOW_OUTSIDE_DATA")


@pytest.mark.parametrize("mutate,code", [
    (lambda b: b.pop("a"), "INVALID_INPUT"),
    (lambda b: b["b"].pop("reinvest"), "INVALID_INPUT"),
    (lambda b: b["a"].__setitem__("strategy", "yearly"), "INVALID_INPUT"),
    (lambda b: b.__setitem__("strategy", "threshold"), "UNKNOWN_FIELD"),
    (lambda b: b["a"].__setitem__("fund", "VOO"), "UNKNOWN_FIELD"),
])
def test_compare_body_validation(client, run, mutate, code):
    body = compare_body(run)
    mutate(body)
    assert_error(client.post("/v1/compare", json=body), 422, code)


# ================================================================ parse

BASIC_CSV = "Date,Amount,Description\n2024-01-03,4.37,COFFEE\n"


def test_parse_documented_example(client):
    r = client.post("/v1/transactions/parse", json=parse_body(BASIC_CSV))
    assert r.status_code == 200, r.text
    b = r.json()
    assert set(b) >= {"columns", "date_column_used", "sign_convention", "transactions", "summary"}
    assert b["columns"] == ["Date", "Amount", "Description"]
    assert b["date_column_used"] == "Date"
    assert b["sign_convention"] == "debits_positive"
    assert len(b["transactions"]) == 1
    t = b["transactions"][0]
    assert t == {"row": 2, "posted_date": "2024-01-03", "amount": "4.37", "direction": "debit",
                 "status": "posted", "category": "purchase", "problem": None}
    s = b["summary"]
    assert s["rows"] == 1 and s["usable"] == 1
    assert s["problems"] == {"invalid_amount": 0, "invalid_date": 0, "zero_amount": 0}
    assert s["non_purchases"] == 0 and s["possible_duplicates"] == 0


def test_parse_row_numbers_count_header_as_line_1(client):
    csv_text = ("Date,Amount,Description\n2024-01-03,4.37,A\n2024-01-04,1.10,B\n"
                "2024-01-05,2.20,C\n")
    b = client.post("/v1/transactions/parse", json=parse_body(csv_text)).json()
    assert [t["row"] for t in b["transactions"]] == [2, 3, 4]
    assert b["summary"]["rows"] == 3


def test_parse_never_returns_descriptions(client):
    csv_text = f"Date,Amount,Description\n2024-01-03,4.37,{DESC_MARKER} PIZZA\n2024-01-04,1.00,{DESC_MARKER}\n"
    r = client.post("/v1/transactions/parse", json=parse_body(csv_text))
    assert r.status_code == 200
    assert DESC_MARKER not in r.text
    assert not find_key(r.json()["transactions"], "description")


def test_parse_does_not_store_anything(client, storage, run):
    client.post("/v1/transactions/parse", json=parse_body(BASIC_CSV))
    client.post("/v1/simulate", json=sim_body(run))
    client.post("/v1/compare", json=compare_body(run))
    assert storage.calls == []


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "＝", "＋", "－", "＠"])
def test_parse_neutralises_echoed_column_names(client, prefix):
    date_col = prefix + "Date"
    other = prefix + "Notes"
    csv_text = f"{date_col},Amount,Description,{other}\n2024-01-03,4.37,COFFEE,x\n"
    r = client.post("/v1/transactions/parse",
                    json=parse_body(csv_text, date=date_col, amount="Amount", description="Description"))
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["date_column_used"] == "'" + date_col
    assert date_col not in b["columns"]
    assert "'" + date_col in b["columns"]
    if any(c.endswith("Notes") for c in b["columns"]):
        assert "'" + other in b["columns"]
    assert "Amount" in b["columns"]  # unaffected names are not altered


@pytest.mark.parametrize("prefix", ["\t", "\r", "\n"])
def test_parse_neutralises_whitespace_prefixed_column_names(client, prefix):
    col = prefix + "Notes"
    csv_text = f'Date,Amount,Description,"{col}"\n2024-01-03,4.37,COFFEE,x\n'
    r = client.post("/v1/transactions/parse", json=parse_body(csv_text))
    if r.status_code != 200:  # ambiguity: a parser may refuse such headers outright
        assert_error(r, 422, "CSV_INVALID")
        return
    for c in r.json()["columns"]:
        assert not c.startswith(("=", "+", "-", "@", "\t", "\r", "\n", "＝", "＋", "－", "＠"))


def test_parse_explicit_debits_negative(client):
    csv_text = "Date,Amount,Description\n2024-01-03,-4.37,COFFEE\n2024-01-04,100.00,SALARY\n"
    r = client.post("/v1/transactions/parse", json=parse_body(csv_text, sign_convention="debits_negative"))
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["sign_convention"] == "debits_negative"
    t1, t2 = b["transactions"]
    assert t1["direction"] == "debit" and Decimal(t1["amount"]) == Decimal("4.37")
    assert t2["direction"] == "credit" and Decimal(t2["amount"]) == Decimal("100")
    for t in b["transactions"]:
        assert AMOUNT_RE.match(t["amount"])


def test_parse_explicit_debits_positive(client):
    csv_text = "Date,Amount,Description\n2024-01-03,4.37,COFFEE\n2024-01-04,-100.00,REFUND\n"
    b = client.post("/v1/transactions/parse", json=parse_body(csv_text, sign_convention="debits_positive")).json()
    assert [t["direction"] for t in b["transactions"]] == ["debit", "credit"]


def test_parse_infers_separate_columns(client):
    csv_text = "Date,Debit,Credit,Description\n2024-01-03,4.37,,COFFEE\n2024-01-04,,100.00,SALARY\n"
    r = client.post("/v1/transactions/parse", json=parse_body(
        csv_text, sign_convention=None, date="Date", debit="Debit", credit="Credit",
        description="Description"))  # EDITED: explicit None (parse_body default changed after contract fix)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["sign_convention"] == "separate_columns"
    assert [t["direction"] for t in b["transactions"]] == ["debit", "credit"]


def test_parse_infers_type_column(client):
    csv_text = ("Date,Amount,Type,Description\n2024-01-03,4.37,debit,COFFEE\n"
                "2024-01-04,100.00,credit,SALARY\n")
    r = client.post("/v1/transactions/parse", json=parse_body(
        csv_text, sign_convention=None, date="Date", amount="Amount", type="Type",
        description="Description"))  # EDITED: explicit None (parse_body default changed after contract fix)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["sign_convention"] == "type_column"
    assert [t["direction"] for t in b["transactions"]] == ["debit", "credit"]


def test_parse_sign_convention_required_when_ambiguous(client):
    csv_text = "Date,Amount,Description\n2024-01-03,-4.37,ITEM A\n2024-01-04,12.50,ITEM B\n"
    err = assert_error(client.post("/v1/transactions/parse", json=parse_body(csv_text, sign_convention=None)), 422,
                       "SIGN_CONVENTION_REQUIRED")  # EDITED: explicit None after the parse_body default changed
    assert "fields" not in err or isinstance(err["fields"], list)


def test_parse_bad_sign_convention_value(client):
    err = assert_error(client.post("/v1/transactions/parse", json=parse_body(BASIC_CSV, sign_convention="positive")),
                       422, "INVALID_INPUT")
    assert "sign_convention" in err["fields"]


def test_parse_problem_rows_are_counted(client):
    csv_text = ("Date,Amount,Description\n2024-01-03,4.37,OK\n2024-01-04,abc,BAD AMOUNT\n"
                "2024-13-45,1.00,BAD DATE\n2024-01-06,0.00,ZERO\n")
    r = client.post("/v1/transactions/parse", json=parse_body(csv_text, sign_convention="debits_positive"))
    assert r.status_code == 200, r.text
    s = r.json()["summary"]
    assert s["rows"] == 4
    assert s["usable"] == 1
    assert s["problems"] == {"invalid_amount": 1, "invalid_date": 1, "zero_amount": 1}
    by_row = {t["row"]: t for t in r.json()["transactions"]}
    assert by_row[2]["problem"] is None
    for row in (3, 4, 5):
        if row in by_row:
            assert by_row[row]["problem"] is not None


def test_parse_flags_possible_duplicates(client):
    csv_text = "Date,Amount,Description\n2024-01-03,4.37,COFFEE\n2024-01-03,4.37,COFFEE\n"
    s = client.post("/v1/transactions/parse", json=parse_body(csv_text)).json()["summary"]
    assert s["possible_duplicates"] >= 1


def test_parse_classifies_and_returns_category(client):
    csv_text = "Date,Amount,Description\n2024-01-03,4.37,COFFEE\n2024-01-04,5.00,ATM WITHDRAWAL\n"
    b = client.post("/v1/transactions/parse", json=parse_body(csv_text)).json()
    for t in b["transactions"]:
        assert t["category"] in ("purchase", "non_purchase")
    assert b["summary"]["non_purchases"] == sum(t["category"] == "non_purchase" for t in b["transactions"])


def test_parse_output_feeds_simulate(client, run):
    d = run.start + timedelta(days=5)
    csv_text = f"Date,Amount,Description\n{d.isoformat()},4.37,COFFEE\n{(d + timedelta(days=1)).isoformat()},12.10,BOOKS\n"
    p = client.post("/v1/transactions/parse", json=parse_body(csv_text)).json()
    allowed = {"posted_date", "amount", "direction", "status", "category"}
    txs = [{k: v for k, v in t.items() if k in allowed} for t in p["transactions"] if t["problem"] is None]
    r = client.post("/v1/simulate", json=sim_body(run, txs=txs))
    assert r.status_code == 200, r.text


def test_parse_is_deterministic(client):
    body = parse_body("Date,Amount,Description\n2024-01-03,4.37,COFFEE\n2024-01-04,2.00,TEA\n")
    assert client.post("/v1/transactions/parse", json=body).json() == \
        client.post("/v1/transactions/parse", json=body).json()


def test_parse_mapped_column_missing(client):
    body = parse_body(BASIC_CSV, date="Posting Date", amount="Amount", description="Description")
    assert_error(client.post("/v1/transactions/parse", json=body), 422, "CSV_INVALID")


def test_parse_mapping_unknown_key(client):
    body = parse_body(BASIC_CSV)
    body["mapping"]["memo"] = "Description"
    err = assert_error(client.post("/v1/transactions/parse", json=body), 422, "UNKNOWN_FIELD")
    assert any(f.startswith("mapping") for f in err["fields"])


def test_parse_accepts_crlf(client):
    r = client.post("/v1/transactions/parse",
                    json=parse_body("Date,Amount,Description\r\n2024-01-03,4.37,COFFEE\r\n"))
    assert r.status_code == 200
    assert r.json()["transactions"][0]["row"] == 2


# ================================================================ saved

@pytest.fixture
def saved_env(keys):
    storage = FakeStorage()
    with make_client(make_app(keys=keys, storage=storage)) as c:
        yield c, storage, default_run(c)


@pytest.mark.parametrize("alg", ["ES256", "RS256"])
def test_saved_success(keys, saved_env, alg):
    c, storage, run = saved_env
    token = sign(keys, claims(), alg=alg)
    r = c.post("/v1/saved", json=saved_body(run), headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    b = r.json()
    assert set(b) == {"id", "result", "meta"}
    assert UUID_RE.match(b["id"])
    assert b["id"] == storage.scenario_id
    check_meta(b["meta"], run)
    check_result(b["result"], b["meta"])

    paths = [req.url.path for req in storage.calls]
    assert paths == ["/rest/v1/scenarios", "/rest/v1/scenario_results"]
    for req in storage.calls:
        assert req.method == "POST"
        assert str(req.url).startswith(SUPABASE_URL + "/rest/v1/")
        assert req.headers["apikey"] == PUBLISHABLE_KEY
        assert req.headers["authorization"] == f"Bearer {token}"
        assert "return=representation" in req.headers["prefer"]
        assert req.headers["content-type"].startswith("application/json")


def test_saved_matches_simulate(keys, saved_env):
    c, storage, run = saved_env
    body = saved_body(run)
    sim = c.post("/v1/simulate", json=sim_body(run)).json()
    r = c.post("/v1/saved", json=body, headers={"Authorization": f"Bearer {sign(keys, claims())}"})
    assert r.status_code == 201
    assert r.json()["result"] == sim["result"]
    assert r.json()["meta"]["input_checksum"] == sim["meta"]["input_checksum"]


def test_saved_without_transactions(keys, saved_env):
    c, storage, run = saved_env
    body = saved_body(run, save_transactions=False, txs=make_txs(run.start, description=DESC_MARKER))
    r = c.post("/v1/saved", json=body, headers={"Authorization": f"Bearer {sign(keys, claims())}"})
    assert r.status_code == 201
    scen = storage.bodies()[0]
    row = scen[0] if isinstance(scen, list) else scen
    assert row.get("transactions") is None
    assert DESC_MARKER not in storage.raw()
    assert DESC_MARKER not in r.text


def test_saved_with_transactions_never_stores_descriptions(keys, saved_env):
    c, storage, run = saved_env
    body = saved_body(run, save_transactions=True, txs=make_txs(run.start, description=DESC_MARKER))
    r = c.post("/v1/saved", json=body, headers={"Authorization": f"Bearer {sign(keys, claims())}"})
    assert r.status_code == 201
    scen = storage.bodies()[0]
    row = scen[0] if isinstance(scen, list) else scen
    assert row.get("transactions"), "transactions should be saved when save_transactions is true"
    assert DESC_MARKER not in storage.raw()
    assert not find_key(storage.bodies(), "description")
    assert DESC_MARKER not in r.text


def test_saved_requires_token(saved_env):
    c, storage, run = saved_env
    assert_error(c.post("/v1/saved", json=saved_body(run)), 401, "AUTH_REQUIRED")
    assert storage.calls == []


def test_saved_storage_unavailable_without_supabase_url(keys):
    app = make_app(keys=keys, supabase_url=None, publishable_key=None)
    with make_client(app) as c:
        run = default_run(c)
        r = c.post("/v1/saved", json=saved_body(run),
                   headers={"Authorization": f"Bearer {sign(keys, claims())}"})
        assert_error(r, 503, "STORAGE_UNAVAILABLE")
        # everything else still works
        assert c.post("/v1/simulate", json=sim_body(run)).status_code == 200
        assert c.get("/v1/health").status_code == 200


@pytest.mark.parametrize("mode", ["connect_error", "timeout"])
def test_saved_storage_not_responding(keys, mode):
    storage = FakeStorage(mode)
    with make_client(make_app(keys=keys, storage=storage)) as c:
        run = default_run(c)
        r = c.post("/v1/saved", json=saved_body(run), headers={"Authorization": f"Bearer {sign(keys, claims())}"})
        assert_error(r, 503, "STORAGE_UNAVAILABLE")


@pytest.mark.parametrize("name,ok", [("a", True), ("x" * 80, True), ("", False), ("x" * 81, False)])
def test_saved_name_length(keys, saved_env, name, ok):
    c, storage, run = saved_env
    r = c.post("/v1/saved", json=saved_body(run, name=name),
               headers={"Authorization": f"Bearer {sign(keys, claims())}"})
    if ok:
        assert r.status_code == 201, r.text
    else:
        err = assert_error(r, 422, "INVALID_INPUT")
        assert "name" in err["fields"]
        assert storage.calls == []


@pytest.mark.parametrize("field,value", [("save_transactions", "true"), ("save_transactions", 1),
                                          ("name", 123)])
def test_saved_strict_types(keys, saved_env, field, value):
    c, storage, run = saved_env
    body = saved_body(run)
    body[field] = value
    r = c.post("/v1/saved", json=body, headers={"Authorization": f"Bearer {sign(keys, claims())}"})
    err = assert_error(r, 422, "INVALID_INPUT")
    assert field in err["fields"]
    assert storage.calls == []


def test_saved_generate_body(keys, saved_env):
    c, storage, run = saved_env
    body = saved_body(run, generate={"seed": 5, "max_per_day": 1})
    r = c.post("/v1/saved", json=body, headers={"Authorization": f"Bearer {sign(keys, claims())}"})
    assert r.status_code == 201, r.text
