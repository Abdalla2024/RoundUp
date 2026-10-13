"""Supabase access-token verification for the save endpoint.

Follows Supabase's guidance: verify against the project's JWKS (asymmetric signing keys),
iss = <SUPABASE_URL>/auth/v1, aud = "authenticated" (supabase.com/docs/guides/auth/jwts,
.../jwt-fields). HS256 (shared-secret) tokens are rejected: Supabase recommends verifying those
with the Auth server instead, which this API does not do.
"""

import uuid

import jwt
from jwt import PyJWKClient, PyJWKSet

from .errors import ApiError

ALLOWED_ALGS = ("ES256", "RS256")


class TokenVerifier:
    def __init__(self, supabase_url: str | None, jwks: dict | None = None):
        self.issuer = f"{supabase_url.rstrip('/')}/auth/v1" if supabase_url else None
        self._static = PyJWKSet.from_dict(jwks) if jwks else None
        # JWKS cached for 5 minutes: Supabase caches it at the edge for 10 and asks clients not to cache longer.
        self._client = (PyJWKClient(f"{self.issuer}/.well-known/jwks.json", lifespan=300, timeout=5)
                        if supabase_url and not jwks else None)

    def _key(self, token: str, kid):
        if self._static is not None:
            for k in self._static.keys:
                if k.key_id == kid:
                    return k
            return None
        return self._client.get_signing_key_from_jwt(token)

    def verify(self, authorization: str | None) -> dict:
        if not self.issuer:
            raise ApiError(503, "STORAGE_UNAVAILABLE", "Saving is not available right now.")
        if not authorization or not authorization.startswith("Bearer ") or not authorization[7:].strip():
            raise ApiError(401, "AUTH_REQUIRED", "Sign in to save scenarios.")
        token = authorization[7:].strip()
        invalid = ApiError(401, "AUTH_INVALID", "Your sign-in is not valid or has expired. Please sign in again.")
        try:
            header = jwt.get_unverified_header(token)
            alg = header.get("alg")
            if alg not in ALLOWED_ALGS:
                raise invalid
            key = self._key(token, header.get("kid"))
            if key is None:
                raise invalid
            claims = jwt.decode(token, key.key if hasattr(key, "key") else key, algorithms=[alg],
                                audience="authenticated", issuer=self.issuer, leeway=10,
                                options={"require": ["exp", "iss", "aud", "sub"]})
        except ApiError:
            raise
        except Exception:                      # any decoding/verification/JWKS failure
            raise invalid from None
        for name in ("exp", "iat", "nbf"):                  # PyJWT does not reject e.g. a string "exp"
            if name in claims and (not isinstance(claims[name], int) or isinstance(claims[name], bool)):
                raise invalid
        try:
            uuid.UUID(str(claims["sub"]))
        except ValueError:
            raise invalid from None
        if claims.get("is_anonymous", False) is not False or claims.get("role", "authenticated") != "authenticated":
            raise invalid
        return claims
