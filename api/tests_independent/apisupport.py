"""Shared helpers for the RoundUp API black-box tests.

Written only from API.md (contract v1). Nothing here depends on the
implementation beyond `roundup_api.main.create_app(...)` as documented.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
import uuid
from datetime import date, timedelta

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

SUPABASE_URL = "https://example-ref.supabase.co"
ISSUER = SUPABASE_URL + "/auth/v1"
PUBLISHABLE_KEY = "test-publishable-key"
AUDIENCE = "authenticated"

ROUTE_KEYS = ("simulate", "compare", "parse", "saved", "read")
# Huge limits for every test that is not about rate limiting, so that a limiter
# whose state leaks between app instances cannot cause spurious 429s.
GENEROUS_LIMITS = {k: 1_000_000 for k in ROUTE_KEYS}

HEX64 = re.compile(r"^[0-9a-f]{64}$")
AMOUNT_RE = re.compile(r"^[0-9]{1,7}(\.[0-9]{1,2})?$")
CENTS_RE = re.compile(r"^-?[0-9]+\.[0-9]{2}$")
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

STRATEGIES = ("threshold", "next_session", "weekly", "monthly")
STYLES = ("broad", "dividend")
LABEL_TEXT = "Synthetic scenario. Not a real fund, not real prices, and not a forecast."

VALIDATION_CODES = {"UNKNOWN_FIELD", "INVALID_INPUT"}
NON_VALIDATION_CODES = {
    "INVALID_JSON", "AUTH_REQUIRED", "AUTH_INVALID", "NOT_FOUND", "METHOD_NOT_ALLOWED",
    "PAYLOAD_TOO_LARGE", "UNSUPPORTED_MEDIA_TYPE", "RATE_LIMITED", "INTERNAL",
    "STORAGE_UNAVAILABLE",
}
ALL_CODES = VALIDATION_CODES | NON_VALIDATION_CODES | {
    "UNKNOWN_SCENARIO", "WINDOW_OUTSIDE_DATA", "SIGN_CONVENTION_REQUIRED", "CSV_INVALID",
}

# Substrings that indicate a stack trace, internal path or framework detail leaked
# into a client-visible body.
LEAK_MARKERS = (
    "Traceback", 'File "', "/Users/", "/home/", "/var/task", "site-packages", ".py\"",
    ".py:", ".py,", "pydantic", "starlette", "uvicorn", "errors.pydantic.dev",
    "{'type'", "'loc'", "NoneType", "KeyError", "ValueError", "TypeError",
    "AttributeError", "RecursionError", "JSONDecodeError", "UnicodeDecodeError",
    "roundup_engine.", "roundup_api.", "roundup_scenarios.", "Exception(",
)

SCRIPT_MARKER = "<script>alert('rU-xss-7f3a')</script>"
DESC_MARKER = "ZZDESCMARKER9Q"  # unique token; must never appear in any response


# ---------------------------------------------------------------- app factory

def make_app(*, keys=None, storage=None, rate_limits=GENEROUS_LIMITS,
             supabase_url=SUPABASE_URL, publishable_key=PUBLISHABLE_KEY):
    from roundup_api.main import create_app  # imported lazily: collection never needs it

    if storage is None:
        storage = FakeStorage()
    return create_app(
        supabase_url=supabase_url,
        publishable_key=publishable_key,
        jwks=keys.jwks if keys is not None else {"keys": []},
        storage_transport=storage.transport,
        rate_limits=rate_limits,
    )


def make_client(app):
    from fastapi.testclient import TestClient

    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------- fake storage

class FakeStorage:
    """Stands in for the Supabase Data API (PostgREST) via httpx.MockTransport."""

    def __init__(self, mode: str = "ok"):
        self.mode = mode
        self.calls: list[httpx.Request] = []
        self.scenario_id = str(uuid.uuid4())
        self.transport = httpx.MockTransport(self.handler)

    def bodies(self):
        out = []
        for req in self.calls:
            try:
                out.append(json.loads(req.content or b"null"))
            except ValueError:
                out.append(None)
        return out

    def raw(self) -> str:
        return "\n".join(req.content.decode("utf-8", "replace") for req in self.calls)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        mode = self.mode
        if mode == "connect_error":
            raise httpx.ConnectError("connection refused", request=request)
        if mode == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        if mode == "server_error":
            return httpx.Response(500, json={"message": "internal-db-detail SECRETPGDETAIL"})
        if mode == "unauthorized":
            return httpx.Response(401, json={"message": "JWT expired SECRETPGDETAIL"})
        if mode == "rls_denied":
            return httpx.Response(403, json={"code": "42501", "message": "new row violates row-level security policy SECRETPGDETAIL"})
        if mode == "not_json":
            return httpx.Response(200, content=b"<html>SECRETPGDETAIL</html>",  # EDITED: 200, as RPC answers
                                  headers={"Content-Type": "text/html"})
        if mode == "empty_array":
            return httpx.Response(201, json=[])
        if mode == "results_fail" and path.endswith("/rest/v1/scenario_results"):
            return httpx.Response(500, json={"message": "SECRETPGDETAIL"})
        try:
            payload = json.loads(request.content or b"null")
        except ValueError:
            payload = None
        # EDITED (stage 5): the contract now saves through one atomic database function. PostgREST returns a
        # scalar function's result as a bare JSON value (docs: references/api/functions.rst, "Scalar functions").
        if path.endswith("/rest/v1/rpc/save_scenario"):
            if mode == "empty_array":
                return httpx.Response(200, json=None)
            return httpx.Response(200, json=self.scenario_id)
        if path.endswith("/rest/v1/scenarios"):
            row = payload[0] if isinstance(payload, list) and payload else payload
            row = dict(row) if isinstance(row, dict) else {}
            row["id"] = self.scenario_id
            return httpx.Response(201, json=[row])
        if path.endswith("/rest/v1/scenario_results"):
            rows = payload if isinstance(payload, list) else [payload]
            created = []
            for r in rows:
                r = dict(r) if isinstance(r, dict) else {}
                r["id"] = str(uuid.uuid4())
                created.append(r)
            return httpx.Response(201, json=created)
        return httpx.Response(404, json={"message": "unexpected path"})


# ---------------------------------------------------------------- JWT / JWKS

def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _to_jwk(alg_cls, public_key) -> dict:
    j = alg_cls.to_jwk(public_key)
    return json.loads(j) if isinstance(j, str) else dict(j)


class Keys:
    def __init__(self):
        self.ec = ec.generate_private_key(ec.SECP256R1())
        self.rsa = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.rogue_ec = ec.generate_private_key(ec.SECP256R1())
        self.rogue_rsa = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.ec_kid = "test-ec-kid"
        self.rsa_kid = "test-rsa-kid"
        ecj = _to_jwk(jwt.algorithms.ECAlgorithm, self.ec.public_key())
        ecj.update({"kid": self.ec_kid, "alg": "ES256", "use": "sig"})
        rsj = _to_jwk(jwt.algorithms.RSAAlgorithm, self.rsa.public_key())
        rsj.update({"kid": self.rsa_kid, "alg": "RS256", "use": "sig"})
        self.jwks = {"keys": [ecj, rsj]}
        self.rsa_public_pem = self.rsa.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


_DROP = object()


def claims(**overrides) -> dict:
    now = int(time.time())
    c = {
        "sub": str(uuid.uuid4()),
        "aud": AUDIENCE,
        "iss": ISSUER,
        "iat": now,
        "exp": now + 3600,
        "role": "authenticated",
        "email": "tester@example.com",
        "is_anonymous": False,
    }
    for k, v in overrides.items():
        if v is _DROP:
            c.pop(k, None)
        else:
            c[k] = v
    return c


DROP = _DROP


def sign(keys: Keys, payload: dict, alg: str = "ES256", kid: str | None = None, key=None) -> str:
    if alg.startswith("ES"):
        key = key or keys.ec
        kid = kid or keys.ec_kid
    else:
        key = key or keys.rsa
        kid = kid or keys.rsa_kid
    # Sign at the JWS layer so PyJWT never second-guesses deliberately bad claims.
    tok = jwt.api_jws.encode(json.dumps(payload, separators=(",", ":")).encode(), key,
                             algorithm=alg, headers={"kid": kid, "typ": "JWT"})
    return tok.decode() if isinstance(tok, bytes) else tok


def raw_token(header: dict, payload: dict, signature: bytes = b"") -> str:
    return b64u(json.dumps(header).encode()) + "." + b64u(json.dumps(payload).encode()) + "." + b64u(signature)


def hs256_token(secret: bytes, header: dict, payload: dict) -> str:
    signing_input = (b64u(json.dumps(header).encode()) + "." + b64u(json.dumps(payload).encode())).encode()
    sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
    return signing_input.decode() + "." + b64u(sig)


# ---------------------------------------------------------------- bodies

def listing(client) -> dict:
    r = client.get("/v1/scenarios")
    assert r.status_code == 200, r.text
    return r.json()


def window_for(style: dict, days: int = 365):
    s = date.fromisoformat(style["start"])
    e = date.fromisoformat(style["end"])
    return s, min(e, s + timedelta(days=days))


class Run:
    def __init__(self, scenario: dict, style: dict, start: date, end: date):
        self.scenario = scenario
        self.style = style
        self.start = start
        self.end = end
        self.scenario_id = scenario["id"]
        self.style_name = style["style"]


def default_run(client, scenario_index: int = 0, style_name: str = "broad") -> Run:
    lst = listing(client)
    sc = lst["scenarios"][scenario_index]
    st = next(x for x in sc["styles"] if x["style"] == style_name)
    s, e = window_for(st)
    return Run(sc, st, s, e)


AMOUNTS = ("4.37", "12.01", "0.99", "25.50", "7")
DESCRIPTIONS = ("COFFEE SHOP", "GROCERY MART", "BOOK STORE", "PETROL STATION", "BAKERY")


def make_txs(start: date, n: int = 5, description: str | None = None, **extra) -> list:
    txs = []
    for i in range(n):
        t = {
            "posted_date": (start + timedelta(days=3 + (7 * i) % 300)).isoformat(),
            "amount": AMOUNTS[i % len(AMOUNTS)],
            "direction": "debit",
            "description": description if description is not None else DESCRIPTIONS[i % len(DESCRIPTIONS)],
        }
        t.update(extra)
        txs.append(t)
    return txs


def minimal_txs(start: date, n: int) -> list:
    d = (start + timedelta(days=3)).isoformat()
    return [{"posted_date": d, "amount": "1", "direction": "debit"} for _ in range(n)]


def sim_body(run: Run, txs=None, generate=None, strategy="threshold", reinvest=True) -> dict:
    body = {
        "scenario_id": run.scenario_id,
        "style": run.style_name,
        "start": run.start.isoformat(),
        "end": run.end.isoformat(),
        "strategy": strategy,
        "reinvest": reinvest,
    }
    if generate is not None:
        body["generate"] = generate
    else:
        body["transactions"] = txs if txs is not None else make_txs(run.start)
    return body


def compare_body(run: Run, a=None, b=None, txs=None, generate=None) -> dict:
    body = sim_body(run, txs=txs, generate=generate)
    body.pop("strategy")
    body.pop("reinvest")
    body["a"] = a or {"strategy": "threshold", "reinvest": True}
    body["b"] = b or {"strategy": "monthly", "reinvest": False}
    return body


def saved_body(run: Run, name="My scenario", save_transactions=False, **kw) -> dict:
    body = sim_body(run, **kw)
    body["name"] = name
    body["save_transactions"] = save_transactions
    return body


MAPPING_KEYS = ("date", "posted_date", "amount", "debit", "credit", "type", "status",
                "description", "external_id", "account")


def mapping(**kw) -> dict:
    m = {k: None for k in MAPPING_KEYS}
    m.update(kw)
    return m


def parse_body(csv_text: str, sign_convention="debits_positive", **map_kw) -> dict:
    # EDITED by the main session after review: the API.md example wrongly showed sign_convention null being
    # inferred as debits_positive, contradicting FINANCE-RULES R-1.3 (no silent default). Contract corrected;
    # the default here now matches the corrected example.
    if not map_kw:
        map_kw = {"date": "Date", "amount": "Amount", "description": "Description"}
    return {"csv": csv_text, "mapping": mapping(**map_kw), "sign_convention": sign_convention}


# ---------------------------------------------------------------- assertions

def assert_no_leak(text: str):
    for m in LEAK_MARKERS:
        assert m not in text, f"response leaks internal detail {m!r}: {text[:500]}"


def assert_error(resp, status, code=None, codes=None) -> dict:
    statuses = status if isinstance(status, (set, tuple, list)) else {status}
    assert resp.status_code in statuses, f"expected {statuses}, got {resp.status_code}: {resp.text[:500]}"
    assert resp.headers.get("x-request-id"), "every response must carry X-Request-ID"
    assert resp.headers.get("content-type", "").startswith("application/json"), resp.headers.get("content-type")
    body = resp.json()
    assert isinstance(body, dict) and set(body) == {"error"}, body
    err = body["error"]
    assert isinstance(err, dict)
    assert set(err) <= {"code", "message", "fields"}, err
    allowed = {code} if code else (set(codes) if codes else ALL_CODES)
    assert err.get("code") in allowed, f"expected code in {allowed}, got {err.get('code')}"
    msg = err.get("message")
    assert isinstance(msg, str) and msg.strip(), "message must be a non-empty sentence"
    assert len(msg) <= 1000, "message should be a short plain-language sentence"
    assert_no_leak(resp.text)
    if err["code"] in VALIDATION_CODES:
        f = err.get("fields")
        assert isinstance(f, list) and f and all(isinstance(x, str) for x in f), err
    elif err["code"] in NON_VALIDATION_CODES:
        assert "fields" not in err, f"fields only for validation errors: {err}"
    return err


def find_key(obj, key) -> bool:
    if isinstance(obj, dict):
        return key in obj or any(find_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(find_key(v, key) for v in obj)
    return False


def post_raw(client, path, data: bytes | str, content_type="application/json", headers=None):
    h = dict(headers or {})
    if content_type is not None:
        h["Content-Type"] = content_type
    if isinstance(data, str):
        data = data.encode("utf-8")
    return client.post(path, content=data, headers=h)
