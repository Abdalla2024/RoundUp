// Saved scenarios are READ and DELETED in the browser through the Supabase Data API with the user's own token, so
// row-level security returns only that user's rows (PLAN.md §4). Saving goes through the API (atomic function).
import { PUBLISHABLE_KEY, SUPABASE_URL } from "./auth";
import type { Result } from "./types";

export interface SavedScenario {
  id: string; name: string; created_at: string;
  config: { scenario_id: string; style: string; start: string; end: string; strategy: string; reinvest: boolean;
            typical?: { per_week: number; average_roundup: string } | null };
  scenario_results: { result: Result; engine_version: string; model_version: string; scenario_seed: number;
                      market_checksum: string; input_checksum: string; created_at: string }[];
}

const headers = (token: string) => ({ apikey: PUBLISHABLE_KEY, Authorization: `Bearer ${token}` });

export async function listSaved(token: string): Promise<SavedScenario[]> {
  const q = "select=id,name,created_at,config,scenario_results(result,engine_version,model_version,scenario_seed,market_checksum,input_checksum,created_at)&order=created_at.desc";
  const r = await fetch(`${SUPABASE_URL}/rest/v1/scenarios?${q}`, { headers: headers(token) });
  if (r.status === 401) throw Object.assign(new Error("expired"), { code: "AUTH" });
  if (!r.ok) throw new Error("Saved scenarios couldn’t be loaded right now. Please try again.");
  return r.json();
}

export async function deleteSaved(token: string, id: string): Promise<void> {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/scenarios?id=eq.${encodeURIComponent(id)}`,
    { method: "DELETE", headers: headers(token) });
  if (!r.ok) throw new Error("That scenario couldn’t be deleted right now. Please try again.");
}
