"""Validation, limits and abuse cases (API.md conventions)."""

import json

import pytest
from conftest import base_body


def post_raw(client, path, data: bytes, ctype="application/json", headers=None):
    h = {"Content-Type": ctype}
    h.update(headers or {})
    return client.post(path, content=data, headers=h)


def err(r):
    return r.json()["error"]["code"]


@pytest.mark.parametrize("mutate,code", [
    (lambda b: b.update(extra=1), "UNKNOWN_FIELD"),
    (lambda b: b["transactions"][0].update(memo="x"), "UNKNOWN_FIELD"),
    (lambda b: b["transactions"][0].update(amount=4.37), "INVALID_INPUT"),          # JSON number, not string
    (lambda b: b["transactions"][0].update(amount="4.375"), "INVALID_INPUT"),
    (lambda b: b["transactions"][0].update(amount="-4.37"), "INVALID_INPUT"),
    (lambda b: b["transactions"][0].update(amount="=1+1"), "INVALID_INPUT"),
    (lambda b: b.update(reinvest="true"), "INVALID_INPUT"),                         # string, not boolean
    (lambda b: b.update(reinvest=1), "INVALID_INPUT"),
    (lambda b: b.update(strategy="lowest-price"), "INVALID_INPUT"),                 # look-ahead strategy (R-5.5)
    (lambda b: b.update(start="2015-02-30"), "INVALID_INPUT"),
    (lambda b: b.update(start="01/02/2015"), "INVALID_INPUT"),
    (lambda b: b.update(generate={"seed": 1, "max_per_day": 1}), "INVALID_INPUT"),  # both sources
    (lambda b: b.pop("transactions"), "INVALID_INPUT"),                              # neither
    (lambda b: b.update(transactions=[]), "INVALID_INPUT"),
    (lambda b: b["transactions"][0].update(description="x" * 141), "INVALID_INPUT"),
    (lambda b: b["transactions"][0].update(direction="sideways"), "INVALID_INPUT"),
])
def test_validation(client, mutate, code):
    body = base_body()
    mutate(body)
    r = client.post("/v1/simulate", json=body)
    assert r.status_code == 422, r.text
    assert err(r) == code
    assert r.json()["error"]["message"] and "Traceback" not in r.text


def test_generate_seed_bounds(client):
    for g in ({"seed": -1, "max_per_day": 1}, {"seed": 2**31, "max_per_day": 1}, {"seed": 1, "max_per_day": 4},
              {"seed": 1.5, "max_per_day": 1}, {"seed": True, "max_per_day": 1}):
        b = base_body()
        b.pop("transactions")
        b["generate"] = g
        assert client.post("/v1/simulate", json=b).status_code == 422, g


def test_too_many_transactions(client):
    b = base_body(transactions=[{"posted_date": "2015-01-05", "amount": "1.10", "direction": "debit"}] * 20001)
    r = client.post("/v1/simulate", json=b)
    assert r.status_code in (413, 422)


def test_max_transactions_accepted(client):
    b = base_body(transactions=[{"posted_date": "2015-01-05", "amount": "1.10", "direction": "debit"}] * 20000)
    assert client.post("/v1/simulate", json=b).status_code == 200


def test_oversize_body_with_content_length(client):
    r = post_raw(client, "/v1/simulate", b"{" + b" " * 3_000_001 + b"}")
    assert r.status_code == 413 and err(r) == "PAYLOAD_TOO_LARGE"


def test_oversize_body_streamed_without_content_length(client):
    def gen():
        for _ in range(31):
            yield b" " * 100_000
    r = client.post("/v1/simulate", content=gen(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_lying_content_length_is_not_trusted(client):
    big = json.dumps(base_body()).encode() + b" " * 3_000_100
    r = post_raw(client, "/v1/simulate", big, headers={"Content-Length": "100"})
    assert r.status_code in (400, 413)


@pytest.mark.parametrize("data", [b"not json", b"[1,2]", b'"x"', b"", b'{"a": NaN}', b'{"a": Infinity}',
                                  b'{"reinvest": true, "reinvest": false}', b"[" * 5000 + b"]" * 5000])
def test_bad_json(client, data):
    r = post_raw(client, "/v1/simulate", data)
    assert r.status_code in (400, 422), (data[:20], r.status_code)
    assert "Traceback" not in r.text


def test_wrong_content_type(client):
    r = post_raw(client, "/v1/simulate", json.dumps(base_body()).encode(), ctype="text/plain")
    assert r.status_code == 415 and err(r) == "UNSUPPORTED_MEDIA_TYPE"


def test_404_405(client):
    assert err(client.get("/v1/nope")) == "NOT_FOUND"
    r = client.get("/v1/simulate")
    assert r.status_code == 405 and err(r) == "METHOD_NOT_ALLOWED"


def test_rate_limit(make_client):
    c = make_client(rate_limits={"simulate": 3})
    codes = [c.post("/v1/simulate", json=base_body()).status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429
    r = c.post("/v1/simulate", json=base_body())
    assert err(r) == "RATE_LIMITED" and int(r.headers["Retry-After"]) >= 1
    assert c.get("/v1/health").status_code == 200       # separate bucket


def test_request_id_not_taken_from_client(client):
    r = client.get("/v1/health", headers={"X-Request-ID": "attacker-chosen"})
    assert r.headers["X-Request-ID"] != "attacker-chosen"


@pytest.mark.parametrize("csv_text", ["Date,Amount\n2015-01-05,4.37\x00\n", "\x89PNG\r\n\x1a\n\x00\x00",
                                      'Date,Amount\n"2015-01-05,4.37\n', ""])
def test_malformed_csv(client, csv_text):
    r = client.post("/v1/transactions/parse", json={"csv": csv_text, "mapping": {"date": "Date", "amount": "Amount"},
                                                   "sign_convention": "debits_positive"})
    assert r.status_code == 422 and err(r) in ("CSV_INVALID", "INVALID_INPUT"), r.text


def test_csv_too_many_rows(client):
    csv_text = "Date,Amount\n" + "2015-01-05,4.37\n" * 20001
    r = client.post("/v1/transactions/parse", json={"csv": csv_text, "mapping": {"date": "Date", "amount": "Amount"},
                                                   "sign_convention": "debits_positive"})
    assert r.status_code == 422 and err(r) == "CSV_INVALID"


def test_csv_text_too_long(client):
    r = client.post("/v1/transactions/parse", json={"csv": "a" * 2_000_001, "mapping": {"date": "Date"}})
    assert r.status_code == 422


def test_injection_strings_are_inert(client):
    nasty = ["<script>alert(1)</script>", "'; DROP TABLE scenarios; --", "{{7*7}}", "${jndi:ldap://x}"]
    for s in nasty:
        b = base_body()
        b["transactions"][0]["description"] = s
        r = client.post("/v1/simulate", json=b)
        assert r.status_code == 200 and s not in r.text


# ---- stage 6: found on the deployed preview ------------------------------------------------------------
def test_unknown_field_names_are_not_echoed_unless_plain(client):
    """A hostile field NAME used to come back verbatim in error.fields. Plain names (letters, digits, _) are kept
    because they help a developer; anything else is replaced by '?'."""
    for hostile in ('<img src=x onerror=alert(1)>', "a b", "x" * 80, "ключ", 'q"; drop', "a.b"):
        r = client.post("/v1/simulate", json={hostile: 1})
        assert r.status_code == 422 and r.json()["error"]["code"] == "UNKNOWN_FIELD", hostile
        fields = r.json()["error"]["fields"]
        assert fields == ["?"], (hostile, fields)
        assert hostile not in r.text
    r = client.post("/v1/simulate", json={"memo": 1})
    assert r.json()["error"]["fields"] == ["memo"]
    body = base_body()
    body["transactions"][0]["memo"] = "x"
    assert client.post("/v1/simulate", json=body).json()["error"]["fields"] == ["transactions.0.memo"]
    body = base_body()
    body["transactions"][0]["<b>"] = "x"
    assert client.post("/v1/simulate", json=body).json()["error"]["fields"] == ["transactions.0.?"]


def test_response_headers_for_a_json_api(client):
    ok = client.get("/v1/health")
    bad = client.post("/v1/simulate", json={})
    for r in (ok, bad):
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
        assert r.headers["referrer-policy"] == "no-referrer"
    assert bad.headers["cache-control"] == "no-store"
    assert client.post("/v1/simulate", json=base_body()).headers["cache-control"] == "no-store"


def test_generate_with_an_impossible_window_fails_fast_with_422(client):
    """Found by the attack agent on the deployed preview: `generate` stepped through every day between start and end
    BEFORE the window was checked, so end=9999-12-31 took 8-10 s and then crashed (500). It must be an instant 422."""
    import time
    gen = {"seed": 1, "max_per_day": 3}
    windows = [("2012-01-03", "9999-12-31"), ("0001-01-01", "9999-12-31"), ("0001-01-01", "2026-09-30"),
               ("2012-01-03", "3000-12-31"), ("2026-10-01", "2026-09-30")]
    for start, end in windows:
        body = {"scenario_id": "steady-growth", "style": "broad", "start": start, "end": end, "generate": gen,
                "strategy": "threshold", "reinvest": True}
        t = time.perf_counter()
        r = client.post("/v1/simulate", json=body)
        assert r.status_code == 422 and r.json()["error"]["code"] == "WINDOW_OUTSIDE_DATA", (start, end, r.text[:200])
        assert time.perf_counter() - t < 1.0, (start, end)
        cmp_body = {k: v for k, v in body.items() if k not in ("strategy", "reinvest")}
        cmp_body.update(a={"strategy": "threshold", "reinvest": True}, b={"strategy": "monthly", "reinvest": False})
        rc = client.post("/v1/compare", json=cmp_body)
        assert rc.status_code == 422 and rc.json()["error"]["code"] == "WINDOW_OUTSIDE_DATA", (start, end)


def test_generate_inside_the_window_is_unchanged(client):
    """The guard must not change any valid run: same request, same numbers as the engine's own generator."""
    from roundup_engine.generator import generate_transactions
    body = {"scenario_id": "steady-growth", "style": "broad", "start": "2015-01-02", "end": "2015-06-30",
            "generate": {"seed": 5, "max_per_day": 2}, "strategy": "threshold", "reinvest": True}
    r = client.post("/v1/simulate", json=body)
    assert r.status_code == 200
    n = len(generate_transactions(seed=5, start="2015-01-02", end="2015-06-30", max_per_day=2))
    assert int(r.json()["result"]["transactions_used"]) + int(r.json()["result"]["transactions_ignored"]) == n
