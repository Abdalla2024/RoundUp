"""Saving through the Supabase Data API with the user's own token, so RLS applies to the API's writes."""

import httpx

from .errors import ApiError

UNAVAILABLE = ApiError(503, "STORAGE_UNAVAILABLE", "Saving is not available right now. Your results were "
                                                   "calculated but not saved. Please try again later.")


class Storage:
    def __init__(self, supabase_url: str | None, publishable_key: str | None, transport=None):
        self.base = f"{supabase_url.rstrip('/')}/rest/v1" if supabase_url else None
        self.key = publishable_key
        self.transport = transport

    def save(self, token: str, params: dict) -> str:
        """One call to the atomic save_scenario() database function (supabase/migrations/0002_rls.sql).
        PostgREST returns a scalar function's result as a bare JSON value: here, the new scenario id."""
        if not self.base or not self.key:
            raise UNAVAILABLE
        try:
            with httpx.Client(transport=self.transport, timeout=5) as client:
                r = client.post(f"{self.base}/rpc/save_scenario", json=params, headers={
                    "apikey": self.key, "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        except httpx.HTTPError:
            raise UNAVAILABLE from None
        if r.status_code != 200:
            raise UNAVAILABLE
        try:
            new_id = r.json()
        except ValueError:
            raise UNAVAILABLE from None
        if not isinstance(new_id, str) or len(new_id) != 36:
            raise UNAVAILABLE
        return new_id
