"""LOCAL TEST STAND-IN for the parts of Supabase RoundUp uses. Never deploy this.

    .venv/bin/python tools/standin/server.py --port 54321 --origin http://localhost:3100

- GET  /auth/v1/.well-known/jwks.json   public key of a fresh ES256 key generated at startup (no real secrets)
- POST /standin/token {"email"}         a signed access token shaped like Supabase's (iss/aud/sub/role/exp)
- POST /rest/v1/rpc/save_scenario       like the SQL function: owner = token's sub; returns the new id (200, bare JSON)
- GET  /rest/v1/scenarios?select=...    only the caller's rows, with nested scenario_results (RLS-like isolation)
- DELETE /rest/v1/scenarios?id=eq.<id>  only if the caller owns it
CORS allows exactly the --origin given.
"""

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

KEY = ec.generate_private_key(ec.SECP256R1())
JWK = json.loads(ECAlgorithm.to_jwk(KEY.public_key()))
JWK.update({"kid": "standin-1", "alg": "ES256", "use": "sig"})
STORE: dict[str, dict] = {}          # scenario id -> row (+ "results": [...])
ARGS = None


def user_of(handler) -> str | None:
    auth = handler.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        claims = jwt.decode(auth[7:], KEY.public_key(), algorithms=["ES256"], audience="authenticated",
                            issuer=f"{ARGS.base}/auth/v1")
    except jwt.PyJWTError:
        return None
    return claims["sub"]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):          # quiet
        pass

    def _send(self, status, body=None):
        data = b"" if body is None else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", ARGS.origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, apikey")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"null")

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/auth/v1/.well-known/jwks.json":
            return self._send(200, {"keys": [JWK]})
        if u.path == "/rest/v1/scenarios":
            sub = user_of(self)
            if not sub:
                return self._send(401, {"message": "JWT invalid"})
            rows = [dict({k: v for k, v in r.items() if k != "results"}, scenario_results=r["results"])
                    for r in STORE.values() if r["user_id"] == sub]
            rows.sort(key=lambda r: r["created_at"], reverse=True)
            return self._send(200, rows)
        return self._send(404, {"message": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/standin/token":
            email = (self._body() or {}).get("email", "")
            sub = str(uuid.uuid5(uuid.NAMESPACE_URL, "roundup-standin:" + email))
            now = int(time.time())
            tok = jwt.encode({"iss": f"{ARGS.base}/auth/v1", "aud": "authenticated", "sub": sub, "role": "authenticated",
                              "email": email, "iat": now, "exp": now + 3600, "is_anonymous": False},
                             KEY, algorithm="ES256", headers={"kid": "standin-1"})
            return self._send(200, {"access_token": tok, "user": {"id": sub, "email": email}})
        if u.path == "/rest/v1/rpc/save_scenario":
            sub = user_of(self)
            if not sub:
                return self._send(401, {"message": "JWT invalid"})
            p = self._body()
            sid = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            STORE[sid] = {"id": sid, "user_id": sub, "name": p["p_name"], "config": p["p_config"],
                          "transactions": p["p_transactions"], "created_at": now,
                          "results": [{"result": p["p_result"], "engine_version": p["p_engine_version"],
                                       "model_version": p["p_model_version"], "scenario_seed": p["p_scenario_seed"],
                                       "market_checksum": p["p_market_checksum"], "input_checksum": p["p_input_checksum"],
                                       "created_at": now}]}
            return self._send(200, sid)
        return self._send(404, {"message": "not found"})

    def do_DELETE(self):
        u = urlparse(self.path)
        sub = user_of(self)
        if u.path == "/rest/v1/scenarios" and sub:
            sid = parse_qs(u.query).get("id", [""])[0].removeprefix("eq.")
            if sid in STORE and STORE[sid]["user_id"] == sub:
                del STORE[sid]
            return self._send(204)
        return self._send(401 if not sub else 404, {"message": "no"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=54321)
    ap.add_argument("--origin", default="http://localhost:3100")
    ARGS = ap.parse_args()
    ARGS.base = f"http://127.0.0.1:{ARGS.port}"
    ThreadingHTTPServer(("127.0.0.1", ARGS.port), H).serve_forever()
