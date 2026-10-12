"""Saving through the Supabase Data API with the user's own token, so RLS applies to the API's writes.

PostgREST: POST /rest/v1/<table> with "Prefer: return=representation" answers 201 and the created rows.
"""

import httpx

from .errors import ApiError

UNAVAILABLE = ApiError(503, "STORAGE_UNAVAILABLE", "Saving is not available right now. Your results were "
                                                   "calculated but not saved. Please try again later.")


class Storage:
    def __init__(self, supabase_url: str | None, publishable_key: str | None, transport=None):
        self.base = f"{supabase_url.rstrip('/')}/rest/v1" if supabase_url else None
        self.key = publishable_key
        self.transport = transport

    def _insert(self, client: httpx.Client, table: str, token: str, row: dict) -> dict:
        try:
            r = client.post(f"{self.base}/{table}", json=row, headers={
                "apikey": self.key, "Authorization": f"Bearer {token}",
                "Prefer": "return=representation", "Content-Type": "application/json"})
        except httpx.HTTPError:
            raise UNAVAILABLE from None
        if r.status_code != 201:
            raise UNAVAILABLE
        try:
            return r.json()[0]
        except (ValueError, IndexError, KeyError, TypeError):
            raise UNAVAILABLE from None

    def save(self, token: str, scenario_row: dict, result_row: dict) -> str:
        if not self.base or not self.key:
            raise UNAVAILABLE
        with httpx.Client(transport=self.transport, timeout=5) as client:
            created = self._insert(client, "scenarios", token, scenario_row)
            scenario_id = created.get("id")
            if not scenario_id:
                raise UNAVAILABLE
            self._insert(client, "scenario_results", token, dict(result_row, scenario_id=scenario_id))
        return scenario_id
