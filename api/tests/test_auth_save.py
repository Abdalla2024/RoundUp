"""POST /v1/saved: Supabase token verification (local JWKS, no real project) and storage via the Data API."""

import time

import jwt
import pytest
from conftest import ISSUER, base_body
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from roundup_engine import run_scenario  # noqa: F401  (equality checked via /v1/simulate)


def save_body(**kw):
    b = base_body(name="My first scenario", save_transactions=False)
    b.update(kw)
    return b


def test_signed_out_cannot_save(client, storage):
    r = client.post("/v1/saved", json=save_body())
    assert r.status_code == 401 and r.json()["error"]["code"] == "AUTH_REQUIRED"
    assert storage.calls == []


def test_signed_out_can_simulate(client):
    assert client.post("/v1/simulate", json=base_body()).status_code == 200


@pytest.mark.parametrize("bad", [
    "garbage", "", "a.b.c",
    lambda mk: mk(exp=int(time.time()) - 60),
    lambda mk: mk(aud="anon"),
    lambda mk: mk(iss="https://evil.supabase.co/auth/v1"),
    lambda mk: mk(sub=None),
    lambda mk: mk(sub="not-a-uuid"),
    lambda mk: mk(is_anonymous=True),
    lambda mk: mk(role="anon"),
    lambda mk: mk(kid="unknown-kid"),
    lambda mk: mk(key=ec.generate_private_key(ec.SECP256R1())),              # not in the JWKS
    lambda mk: mk(key="test-publishable-key", alg="HS256"),                  # HS256 with a public value
    lambda mk: jwt.encode({"iss": ISSUER, "aud": "authenticated", "sub": "00000000-0000-0000-0000-000000000000",
                           "exp": int(time.time()) + 600}, None, algorithm="none"),
    lambda mk: (lambda t: t[:-4] + ("AAAA" if not t.endswith("AAAA") else "BBBB"))(mk()),  # tampered signature
])
def test_bad_tokens_rejected(client, storage, make_token, bad):
    token = bad(make_token) if callable(bad) else bad
    r = client.post("/v1/saved", json=save_body(), headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, r.text
    assert r.json()["error"]["code"] in ("AUTH_INVALID", "AUTH_REQUIRED")
    assert storage.calls == []


def test_tampered_payload_rejected(client, make_token):
    head, payload, sig = make_token().split(".")
    other_payload = make_token().split(".")[1]
    r = client.post("/v1/saved", json=save_body(),
                    headers={"Authorization": f"Bearer {head}.{other_payload}.{sig}"})
    assert r.status_code == 401


def test_save_success_forwards_user_token(client, storage, make_token):
    token = make_token(sub="11111111-2222-3333-4444-555555555555")
    r = client.post("/v1/saved", json=save_body(), headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    out = r.json()
    sim = client.post("/v1/simulate", json=base_body()).json()
    assert out["result"] == sim["result"] and out["meta"] == sim["meta"]
    assert [c["url"].split("/rest/v1/")[1] for c in storage.calls] == ["scenarios", "scenario_results"]
    for c in storage.calls:
        assert c["headers"]["authorization"] == f"Bearer {token}"         # RLS applies to the API's writes
        assert c["headers"]["apikey"] == "test-publishable-key"
        assert c["headers"]["prefer"] == "return=representation"
    scen, res = storage.calls[0]["body"], storage.calls[1]["body"]
    assert scen["user_id"] == "11111111-2222-3333-4444-555555555555" and scen["name"] == "My first scenario"
    assert scen["transactions"] is None                                    # save_transactions false
    assert res["scenario_id"] == out["id"] and res["result"] == out["result"]
    assert res["engine_version"] and res["market_checksum"] == out["meta"]["market_checksum"]
    assert "COFFEE" not in str(storage.calls)                               # descriptions never stored (D-8)


def test_save_transactions_without_descriptions(client, storage, make_token):
    r = client.post("/v1/saved", json=save_body(save_transactions=True),
                    headers={"Authorization": f"Bearer {make_token()}"})
    assert r.status_code == 201
    saved = storage.calls[0]["body"]["transactions"]
    assert len(saved) == 3 and all("description" not in t for t in saved)
    assert "COFFEE" not in str(storage.calls)


def test_rsa_key_also_accepted(make_client, storage):
    from jwt.algorithms import RSAAlgorithm
    import json
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update({"kid": "rsa-1", "alg": "RS256"})
    c = make_client(jwks={"keys": [jwk]})
    tok = jwt.encode({"iss": ISSUER, "aud": "authenticated", "sub": "11111111-2222-3333-4444-555555555555",
                      "role": "authenticated", "exp": int(time.time()) + 600}, key, algorithm="RS256",
                     headers={"kid": "rsa-1"})
    assert c.post("/v1/saved", json=save_body(), headers={"Authorization": f"Bearer {tok}"}).status_code == 201


def test_storage_failure_is_503(client, storage, make_token):
    storage.fail_on = "scenarios"
    r = client.post("/v1/saved", json=save_body(), headers={"Authorization": f"Bearer {make_token()}"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "STORAGE_UNAVAILABLE"
    assert "boom" not in r.text


def test_not_configured_is_503(make_client, make_token):
    c = make_client(supabase_url=None)
    r = c.post("/v1/saved", json=save_body(), headers={"Authorization": f"Bearer {make_token()}"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "STORAGE_UNAVAILABLE"


def test_name_required_and_bounded(client, make_token):
    h = {"Authorization": f"Bearer {make_token()}"}
    assert client.post("/v1/saved", json=save_body(name=""), headers=h).status_code == 422
    assert client.post("/v1/saved", json=save_body(name="x" * 81), headers=h).status_code == 422


@pytest.mark.parametrize("value", ["true", "false", 1, None])
def test_is_anonymous_must_be_boolean_false_if_present(client, storage, make_token, value):
    tok = make_token(is_anonymous=value) if value is not None else make_token(is_anonymous=None)
    r = client.post("/v1/saved", json=save_body(), headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == (201 if value is None else 401)
