"""Display-only fields added for the redesign (stage 6): the scenario sparkline shape and the end-value composition (R-13.4)."""

from conftest import base_body
from roundup_scenarios import get_published, shape


def test_each_scenario_style_carries_its_shape(client):
    data = client.get("/v1/scenarios").json()
    for sc in data["scenarios"]:
        for st in sc["styles"]:
            assert st["shape"] == shape(get_published(sc["id"], st["style"]))      # passed through, never recomputed here
            assert len(st["shape"]) == 40 and all(isinstance(x, int) and 0 <= x <= 100 for x in st["shape"])


def test_results_carry_the_composition_and_its_shares_add_up(client):
    body = {"scenario_id": "steady-growth", "style": "broad", "start": "2024-01-01", "end": "2024-02-25",
            "typical": {"per_week": 5, "average_roundup": "0.50"}, "strategy": "threshold", "reinvest": True}
    comp = client.post("/v1/simulate", json=body).json()["result"]["summary"]["composition"]
    assert [c["key"] for c in comp] == ["shares", "roundups_waiting", "dividends_as_cash", "receivables"]
    assert sum(c["share_bp"] for c in comp) == 10000
    assert all(isinstance(c["share_bp"], int) and isinstance(c["amount"], str) for c in comp)


def test_compare_results_carry_it_on_both_sides(client):
    body = base_body(a={"strategy": "threshold", "reinvest": True}, b={"strategy": "monthly", "reinvest": False})
    for k in ("strategy", "reinvest"):
        body.pop(k)
    out = client.post("/v1/compare", json=body).json()
    for side in ("a", "b"):
        assert sum(c["share_bp"] for c in out[side]["summary"]["composition"]) == 10000
