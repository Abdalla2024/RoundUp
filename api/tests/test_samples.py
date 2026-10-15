"""The sample bank exports in samples/ (stage 6): reproducible, parsed correctly, and run with the numbers worked out
by construction in samples/make_samples.py (not by calling the parser or the engine)."""

import importlib.util
import json
import pathlib

import pytest
from conftest import base_body

SAMPLES = pathlib.Path(__file__).resolve().parents[2] / "samples"
spec = importlib.util.spec_from_file_location("make_samples", SAMPLES / "make_samples.py")
make = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make)
EXPECTED = json.loads((SAMPLES / "expected.json").read_text())

CASES = {
    "sample-transactions.csv": ("debits_positive", {"date": "Date", "amount": "Amount", "description": "Description", "status": "Status"}),
    "sample-split-columns.csv": ("separate_columns", {"date": "Date", "debit": "Money out", "credit": "Money in", "description": "Description", "status": "Status"}),
    "sample-type-column.csv": ("type_column", {"date": "Date", "amount": "Amount", "type": "Type", "description": "Description", "status": "Status"}),
}


def test_the_files_are_exactly_what_the_script_produces():
    for name, text in {**make.files(), "expected.json": json.dumps(make.expected(), indent=1) + "\n"}.items():
        assert (SAMPLES / name).read_text() == text, f"{name} is out of date: run samples/make_samples.py"


@pytest.mark.parametrize("name", sorted(CASES))
def test_parse_and_simulate_match_the_numbers_worked_out_by_construction(client, name):
    convention, mapping = CASES[name]
    r = client.post("/v1/transactions/parse", json={"csv": (SAMPLES / name).read_text(), "mapping": mapping, "sign_convention": convention})
    assert r.status_code == 200, r.text
    out = r.json()
    s = out["summary"]
    for key, want in EXPECTED["parse_summary"].items():
        assert s[key] == want, (name, key, s)
    assert s["problems"] == {"invalid_amount": 0, "invalid_date": 0, "zero_amount": 0} and s["possible_duplicates"] == 0
    assert out["sign_convention"] == convention
    txs = [{k: x[k] for k in ("posted_date", "amount", "direction", "status", "category")} for x in out["transactions"] if x["problem"] is None]
    body = base_body(scenario_id="steady-growth", start=EXPECTED["window"]["start"], end=EXPECTED["window"]["end"], transactions=txs)
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200, res.text
    result = res.json()["result"]
    assert result["transactions_used"] == str(EXPECTED["simulate"]["transactions_used"])
    assert result["transactions_ignored"] == str(EXPECTED["simulate"]["transactions_ignored"])
    assert result["summary"]["contributed"] == EXPECTED["simulate"]["contributed"]


def test_the_ignored_rows_are_the_right_ones(client):
    convention, mapping = CASES["sample-transactions.csv"]
    out = client.post("/v1/transactions/parse", json={"csv": (SAMPLES / "sample-transactions.csv").read_text(),
                                                      "mapping": mapping, "sign_convention": convention}).json()
    lines = (SAMPLES / "sample-transactions.csv").read_text().splitlines()
    by_row = {x["row"]: x for x in out["transactions"]}
    ignored = {}
    for n, line in enumerate(lines, start=1):
        if n == 1:
            continue
        x = by_row[n]
        why = ("credit" if x["direction"] == "credit" else "non_purchase" if x["category"] == "non_purchase"
               else x["status"] if x["status"] != "posted" else None)
        if why:
            ignored[line.split(",")[1]] = why
    assert ignored == {"Bookshop refund": "credit", "Online shop refund": "credit", "Transfer to savings": "non_purchase",
                       "Card payment": "non_purchase", "Maple Grocery": "pending", "Bakery": "cancelled",
                       "Gym membership": "unrecognised"}


def test_the_typical_sample_file_gives_the_same_result_as_typical_spending(client):
    """samples/sample-typical-5-per-week.csv follows rule R-1.9 (written out independently); uploading it must equal the website's
    typical-spending mode with 5 a week and a 50-cent average."""
    want = EXPECTED["typical_5x8"]
    out = client.post("/v1/transactions/parse", json={"csv": (SAMPLES / "sample-typical-5-per-week.csv").read_text(),
        "mapping": {"date": "Date", "amount": "Amount", "description": "Description", "status": "Status"}, "sign_convention": "debits_positive"}).json()
    assert out["summary"]["rows"] == want["rows"] and out["summary"]["purchases"] == want["purchases"]
    txs = [{k: x[k] for k in ("posted_date", "amount", "direction", "status", "category")} for x in out["transactions"]]
    window = {"start": want["window"]["start"], "end": want["window"]["end"], "scenario_id": "steady-growth", "style": "broad"}
    uploaded = client.post("/v1/simulate", json={**window, "transactions": txs, "strategy": "threshold", "reinvest": True}).json()
    typical = client.post("/v1/simulate", json={**window, "typical": {"per_week": 5, "average_roundup": "0.50"},
                                                "strategy": "threshold", "reinvest": True}).json()
    assert uploaded["result"]["summary"]["contributed"] == typical["result"]["summary"]["contributed"] == want["contributed"]
    assert uploaded["result"] == typical["result"] and uploaded["meta"]["input_checksum"] == typical["meta"]["input_checksum"]
