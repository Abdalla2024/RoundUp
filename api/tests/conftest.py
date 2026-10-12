"""Local test doubles: an ES256 signing key + JWKS (no real Supabase project), and a mock Data API."""

import json
import time
import uuid

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm

from roundup_api.main import create_app

SUPABASE_URL = "https://example-ref.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
KID = "test-key-1"


@pytest.fixture(scope="session")
def ec_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(scope="session")
def jwks(ec_key):
    jwk = json.loads(ECAlgorithm.to_jwk(ec_key.public_key()))
    jwk.update({"kid": KID, "alg": "ES256", "use": "sig"})
    return {"keys": [jwk]}


@pytest.fixture
def make_token(ec_key):
    def _make(key=None, alg="ES256", kid=KID, **overrides):
        now = int(time.time())
        claims = {"iss": ISSUER, "aud": "authenticated", "sub": str(uuid.uuid4()), "role": "authenticated",
                  "exp": now + 600, "iat": now, "is_anonymous": False}
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, key or ec_key, algorithm=alg, headers={"kid": kid})
    return _make


class Storage:
    """Records Data API calls; answers like PostgREST with Prefer: return=representation (201 + array)."""

    def __init__(self):
        self.calls, self.fail_on = [], None

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.calls.append({"url": str(request.url), "headers": dict(request.headers), "body": body})
        table = request.url.path.rsplit("/", 1)[-1]
        if self.fail_on == table:
            return httpx.Response(500, json={"message": "boom"})
        row = dict(body, id=str(uuid.uuid4()))
        return httpx.Response(201, json=[row])


@pytest.fixture
def storage():
    return Storage()


@pytest.fixture
def make_client(jwks, storage):
    def _make(**kw):
        args = dict(supabase_url=SUPABASE_URL, publishable_key="test-publishable-key", jwks=jwks,
                    storage_transport=httpx.MockTransport(storage.handler))
        args.update(kw)
        return TestClient(create_app(**args), raise_server_exceptions=False)
    return _make


@pytest.fixture
def client(make_client):
    return make_client()


def base_body(**kw):
    body = {"scenario_id": "steady-growth", "style": "broad", "start": "2015-01-02", "end": "2016-12-30",
            "strategy": "threshold", "reinvest": True,
            "transactions": [{"posted_date": "2015-01-05", "amount": "4.37", "direction": "debit"},
                             {"posted_date": "2015-01-06", "amount": "3.10", "direction": "debit",
                              "description": "COFFEE"},
                             {"posted_date": "2015-02-02", "amount": "512.37", "direction": "debit",
                              "description": "PAYMENT TO CARD"}]}
    body.update(kw)
    return body
