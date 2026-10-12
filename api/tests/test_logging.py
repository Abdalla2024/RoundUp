"""Request logs: one JSON line per request, no personal data (no IPs, bodies, descriptions, amounts)."""

import json
import logging

from conftest import base_body


def test_access_log_has_no_personal_data(client, caplog):
    caplog.set_level(logging.INFO, logger="roundup_api.access")
    b = base_body()
    b["transactions"][1]["description"] = "SECRET MERCHANT NAME"
    client.post("/v1/simulate", json=b, headers={"X-Forwarded-For": "203.0.113.9"})
    client.post("/v1/simulate", json={"bad": 1})
    lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == "roundup_api.access"]
    assert len(lines) == 2
    ok, bad = lines
    assert ok["route"] == "/v1/simulate" and ok["status"] == 200 and isinstance(ok["latency_ms"], int)
    assert ok["engine_version"] and ok["request_id"] and len(ok["client"]) == 12
    assert bad["status"] == 422 and bad["error_code"] == "UNKNOWN_FIELD"
    text = " ".join(r.getMessage() for r in caplog.records)
    for leaked in ("SECRET MERCHANT", "203.0.113.9", "4.37", "512.37", "testclient"):
        assert leaked not in text


def test_slow_requests_flagged(make_client, caplog):
    caplog.set_level(logging.INFO, logger="roundup_api.access")
    c = make_client(slow_ms=0)
    c.get("/v1/health")
    line = json.loads([r for r in caplog.records if r.name == "roundup_api.access"][-1].getMessage())
    assert line["slow"] is True
