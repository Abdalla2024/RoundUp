"""Capture REAL API responses as component-test fixtures (no hand-typed numbers).

    PYTHONPATH=engine/src:api .venv/bin/python web/tests/fixtures/build_fixtures.py
"""

import json
import pathlib

from fastapi.testclient import TestClient

from roundup_api.main import create_app

OUT = pathlib.Path(__file__).resolve().parent
c = TestClient(create_app(rate_limits={"simulate": 999, "compare": 999, "parse": 999}))
BASE = {"scenario_id": "crash-and-recovery", "style": "broad", "start": "2015-01-02", "end": "2024-12-31",
        "generate": {"seed": 42, "max_per_day": 2}, "buys": "none"}


def save(name, data):
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=1))


save("scenarios", c.get("/v1/scenarios").json())
save("assumptions", c.get("/v1/assumptions").json())
save("simulate", {"request": dict(BASE, strategy="threshold", reinvest=True),
                  "response": c.post("/v1/simulate", json=dict(BASE, strategy="threshold", reinvest=True)).json()})
save("simulate_short", {"request": dict(BASE, scenario_id="steady-growth", start="2012-01-03", end="2012-12-31",
                                        strategy="next_session", reinvest=True),
                        "response": c.post("/v1/simulate", json=dict(BASE, scenario_id="steady-growth", start="2012-01-03",
                                           end="2012-12-31", strategy="next_session", reinvest=True)).json()})
whole = {k: v for k, v in BASE.items() if k != "generate"}
whole["transactions"] = [{"posted_date": "2015-01-05", "amount": "4.00", "direction": "debit"}]
save("simulate_whole_dollar", {"request": dict(whole, strategy="threshold", reinvest=True),
                               "response": c.post("/v1/simulate", json=dict(whole, strategy="threshold", reinvest=True)).json()})
ab = {"a": {"strategy": "threshold", "reinvest": True}, "b": {"strategy": "monthly", "reinvest": False}}
save("compare", {"request": dict(BASE, **ab), "response": c.post("/v1/compare", json=dict(BASE, **ab)).json()})
csv = ("Date,Amount,Description\n2015-01-05,4.37,COFFEE\n2015-01-06,-20.00,REFUND\n"
       "2015-01-07,512.37,PAYMENT TO CARD\n2015-01-08,4.375,BAD\n")
save("parse", {"csv": csv, "response": c.post("/v1/transactions/parse", json={
    "csv": csv, "mapping": {"date": "Date", "amount": "Amount", "description": "Description"},
    "sign_convention": "debits_positive"}).json()})
print("fixtures written:", sorted(p.name for p in OUT.glob("*.json")))
