-- Row-level security and grants. Run after 0001_schema.sql.
-- Supabase: "Enable RLS on every table in an exposed schema." and "On projects that still grant anon and
-- authenticated by default, revoke those grants. Adding policies doesn't remove them."
-- (supabase.com/docs/guides/database/postgres/row-level-security)

alter table public.scenarios        enable row level security;
alter table public.scenario_results enable row level security;
alter table public.explainer_usage  enable row level security;

revoke all on public.scenarios, public.scenario_results, public.explainer_usage from anon, authenticated;
revoke all on function public.touch_updated_at() from public, anon, authenticated;

-- Signed-in users: only what the app needs. Signed-out (anon): nothing.
grant select, insert, delete on public.scenarios to authenticated;
grant update (name) on public.scenarios to authenticated;          -- renaming only
grant select, insert, delete on public.scenario_results to authenticated;   -- no update: results are immutable
grant select on public.explainer_usage to authenticated;            -- writes only via record_explainer_usage()

-- Policies: (select auth.uid()) = user_id, as in Supabase's documented pattern.
create policy "own scenarios: read"   on public.scenarios for select to authenticated using ((select auth.uid()) = user_id);
create policy "own scenarios: create" on public.scenarios for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "own scenarios: rename" on public.scenarios for update to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "own scenarios: delete" on public.scenarios for delete to authenticated using ((select auth.uid()) = user_id);

create policy "own results: read"   on public.scenario_results for select to authenticated using ((select auth.uid()) = user_id);
create policy "own results: create" on public.scenario_results for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "own results: delete" on public.scenario_results for delete to authenticated using ((select auth.uid()) = user_id);

create policy "own usage: read" on public.explainer_usage for select to authenticated using ((select auth.uid()) = user_id);

-- Atomic save: both rows in one transaction (fixes the orphan-scenario case noted in API.md #34).
-- SECURITY INVOKER (Supabase: "Prefer security invoker"), so the caller's RLS policies still apply.
create function public.save_scenario(
  p_name text, p_config jsonb, p_transactions jsonb,
  p_market_scenario text, p_style text, p_strategy text, p_reinvest boolean, p_result jsonb,
  p_engine_version text, p_model_version text, p_scenario_seed integer, p_data_kind text, p_data_end date,
  p_market_checksum text, p_input_checksum text
) returns uuid
language plpgsql security invoker set search_path = '' as $$
declare
  v_user uuid := auth.uid();
  v_id uuid;
begin
  if v_user is null then
    raise exception 'not signed in' using errcode = '42501';
  end if;
  insert into public.scenarios (user_id, name, config, transactions)
  values (v_user, p_name, p_config, p_transactions) returning id into v_id;
  insert into public.scenario_results (scenario_id, user_id, market_scenario, style, strategy, reinvest, result,
      engine_version, model_version, scenario_seed, data_kind, data_end, market_checksum, input_checksum)
  values (v_id, v_user, p_market_scenario, p_style, p_strategy, p_reinvest, p_result,
      p_engine_version, p_model_version, p_scenario_seed, p_data_kind, p_data_end, p_market_checksum, p_input_checksum);
  return v_id;
end $$;

revoke all on function public.save_scenario(text, jsonb, jsonb, text, text, text, boolean, jsonb, text, text,
  integer, text, date, text, text) from public, anon;
grant execute on function public.save_scenario(text, jsonb, jsonb, text, text, text, boolean, jsonb, text, text,
  integer, text, date, text, text) to authenticated;

-- Explainer usage counter: the only writer of explainer_usage. SECURITY DEFINER because users have no write
-- grant; it touches only the caller's own row, with bounded increments. Supabase: "When you use security
-- definer, you must set the search_path."
create function public.record_explainer_usage(p_input_tokens integer, p_output_tokens integer)
returns void
language plpgsql security definer set search_path = '' as $$
declare
  v_user uuid := auth.uid();
begin
  if v_user is null then
    raise exception 'not signed in' using errcode = '42501';
  end if;
  if p_input_tokens not between 0 and 200000 or p_output_tokens not between 0 and 10000 then
    raise exception 'token counts out of range' using errcode = '22003';
  end if;
  insert into public.explainer_usage (user_id, day, requests, input_tokens, output_tokens)
  values (v_user, current_date, 1, p_input_tokens, p_output_tokens)
  on conflict (user_id, day) do update
    set requests = public.explainer_usage.requests + 1,
        input_tokens = public.explainer_usage.input_tokens + excluded.input_tokens,
        output_tokens = public.explainer_usage.output_tokens + excluded.output_tokens;
end $$;

revoke all on function public.record_explainer_usage(integer, integer) from public, anon;
grant execute on function public.record_explainer_usage(integer, integer) to authenticated;
