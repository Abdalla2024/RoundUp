"""Typical spending through the API (R-1.9, stage 6): `typical: {per_week, average_roundup}` instead of transactions or generate."""

import pytest
from conftest import base_body


def typical_body(per_week=5, average="0.50", start="2024-01-01", end="2024-02-25", **kw):
    b = {"scenario_id": "steady-growth", "style": "broad", "start": start, "end": end,
         "typical": {"per_week": per_week, "average_roundup": average}, "strategy": "threshold", "reinvest": True}
    b.update(kw)
    return b


def test_five_a_week_for_eight_weeks_at_fifty_cents_is_twenty_dollars(client):
    r = client.post("/v1/simulate", json=typical_body())
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    assert (res["summary"]["contributed"], res["transactions_used"], res["transactions_ignored"]) == ("20.00", "40", "0")


def test_twenty_a_week_for_a_year_is_five_hundred_twenty_dollars(client):
    res = client.post("/v1/simulate", json=typical_body(20, "0.50", "2024-01-01", "2024-12-29")).json()["result"]
    assert (res["summary"]["contributed"], res["transactions_used"]) == ("520.00", "1040")


@pytest.mark.parametrize("n,avg,start,end,used,contrib", [
    (1, "0.01", "2024-01-01", "2024-01-28", "4", "0.04"),          # minimum inputs
    (60, "0.99", "2024-01-01", "2024-01-07", "60", "59.40"),       # maximum inputs
    (10, "0.25", "2024-01-01", "2024-01-28", "40", "10.00"),       # a non-default average
    (5, "0.50", "2024-01-03", "2024-01-14", "8", "4.00"),          # the window starts mid-week
])
def test_worked_by_hand(client, n, avg, start, end, used, contrib):
    res = client.post("/v1/simulate", json=typical_body(n, avg, start, end)).json()["result"]
    assert (res["transactions_used"], res["summary"]["contributed"]) == (used, contrib)


def test_it_is_deterministic_and_the_checksum_follows_the_inputs(client):
    a1, a2 = (client.post("/v1/simulate", json=typical_body()).json() for _ in range(2))
    assert a1 == a2
    other = client.post("/v1/simulate", json=typical_body(6)).json()
    assert other["meta"]["input_checksum"] != a1["meta"]["input_checksum"]
    assert client.post("/v1/simulate", json=typical_body(average="0.51")).json()["meta"]["input_checksum"] != a1["meta"]["input_checksum"]


def test_compare_accepts_typical(client):
    body = typical_body()
    for k in ("strategy", "reinvest"):
        body.pop(k)
    body.update(a={"strategy": "threshold", "reinvest": True}, b={"strategy": "monthly", "reinvest": False})
    r = client.post("/v1/compare", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["a"]["summary"]["contributed"] == r.json()["b"]["summary"]["contributed"] == "20.00"


@pytest.mark.parametrize("typical", [
    {"per_week": 0, "average_roundup": "0.50"}, {"per_week": 61, "average_roundup": "0.50"}, {"per_week": 5.5, "average_roundup": "0.50"},
    {"per_week": "5", "average_roundup": "0.50"}, {"per_week": True, "average_roundup": "0.50"}, {"per_week": -1, "average_roundup": "0.50"},
    {"per_week": 5, "average_roundup": "0.00"}, {"per_week": 5, "average_roundup": "1.00"}, {"per_week": 5, "average_roundup": "0.5"},
    {"per_week": 5, "average_roundup": "0.505"}, {"per_week": 5, "average_roundup": ".50"}, {"per_week": 5, "average_roundup": 0.5},
    {"per_week": 5, "average_roundup": "-0.50"}, {"per_week": 5}, {"average_roundup": "0.50"}, {}, None,
    {"per_week": 5, "average_roundup": "0.50", "extra": 1},
])
def test_bad_typical_inputs_are_refused_with_a_422(client, typical):
    body = typical_body()
    body["typical"] = typical
    r = client.post("/v1/simulate", json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] in ("INVALID_INPUT", "UNKNOWN_FIELD"), (typical, r.text)


def test_exactly_one_purchase_source(client):
    both = typical_body(generate={"seed": 1, "max_per_day": 1})
    assert client.post("/v1/simulate", json=both).status_code == 422
    with_tx = typical_body(transactions=base_body()["transactions"])
    assert client.post("/v1/simulate", json=with_tx).status_code == 422
    none = typical_body(); none.pop("typical")
    assert client.post("/v1/simulate", json=none).status_code == 422


def test_an_impossible_window_fails_fast(client):
    r = client.post("/v1/simulate", json=typical_body(start="0001-01-01", end="9999-12-31"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "WINDOW_OUTSIDE_DATA"


def test_saving_a_typical_run_keeps_its_inputs_and_never_a_purchase_list(client, storage, make_token):
    token = make_token(sub="11111111-2222-3333-4444-555555555555")
    body = typical_body(name="Typical week", save_transactions=True)
    r = client.post("/v1/saved", json=body, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    p = storage.calls[0]["body"]
    assert p["p_transactions"] is None
    assert p["p_config"]["typical"] == {"per_week": 5, "average_roundup": "0.50"} and p["p_config"]["generate"] is None
