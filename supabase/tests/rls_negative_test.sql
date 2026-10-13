-- RoundUp RLS negative tests: user B must not read or change user A's rows, and signed-out users get nothing.
-- Run in the Supabase SQL editor (it runs as `postgres`). Everything happens inside one transaction that is
-- ROLLED BACK at the end, so no test data stays behind.
--
-- BEFORE RUNNING: create two test users (Authentication > Users > Add user), then replace the two UUIDs below.
-- Impersonation uses the same settings Supabase's auth.uid() reads (request.jwt.claims ->> 'sub').
-- The script stops at the first failure with "FAIL: ...". Success ends with the row 'ALL RLS CHECKS PASSED'.

begin;

select set_config('test.user_a', '00000000-0000-0000-0000-00000000000a', true);   -- <-- replace with user A's id
select set_config('test.user_b', '00000000-0000-0000-0000-00000000000b', true);   -- <-- replace with user B's id

-- ---------------------------------------------------------------- user A saves a scenario
set local role authenticated;
select set_config('request.jwt.claims', json_build_object('sub', current_setting('test.user_a'), 'role', 'authenticated')::text, true);

do $$
declare v_id uuid;
begin
  v_id := public.save_scenario('A private', '{"strategy":"threshold"}', null, 'steady-growth', 'broad', 'threshold',
           true, '{"status":"ok"}', '0.2.0', 'scenario-model-1', 1101, 'sample', '2026-09-30',
           repeat('a', 64), repeat('b', 64));
  perform set_config('test.a1', v_id::text, true);
  if (select count(*) from public.scenario_results where scenario_id = v_id) <> 1 then
    raise exception 'FAIL: save_scenario did not store exactly one result';
  end if;
  raise notice 'PASS: user A saved scenario % with its result (atomic save)', v_id;
end $$;

-- ---------------------------------------------------------------- user B: must not see or touch A's rows
select set_config('request.jwt.claims', json_build_object('sub', current_setting('test.user_b'), 'role', 'authenticated')::text, true);

do $$
declare n int; a1 uuid := current_setting('test.a1')::uuid; a uuid := current_setting('test.user_a')::uuid;
begin
  select count(*) into n from public.scenarios where user_id = a;
  if n <> 0 then raise exception 'FAIL: B can read % of A''s scenarios', n; end if;
  select count(*) into n from public.scenario_results where user_id = a or scenario_id = a1;
  if n <> 0 then raise exception 'FAIL: B can read A''s results'; end if;
  raise notice 'PASS: B cannot read A''s scenarios or results';

  update public.scenarios set name = 'hijacked' where id = a1;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'FAIL: B renamed A''s scenario'; end if;
  delete from public.scenarios where id = a1;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'FAIL: B deleted A''s scenario'; end if;
  delete from public.scenario_results where scenario_id = a1;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'FAIL: B deleted A''s results'; end if;
  raise notice 'PASS: B cannot rename or delete A''s rows (0 rows affected)';

  begin
    insert into public.scenarios (user_id, name, config) values (a, 'planted', '{}');
    raise exception 'FAIL: B inserted a scenario owned by A';
  exception when insufficient_privilege then raise notice 'PASS: B cannot create a scenario as A (RLS)';
  end;

  begin
    insert into public.scenario_results (scenario_id, user_id, market_scenario, style, strategy, reinvest, result,
      engine_version, model_version, scenario_seed, data_kind, data_end, market_checksum, input_checksum)
    values (a1, current_setting('test.user_b')::uuid, 'x', 'broad', 'threshold', true, '{}', 'v', 'm', 1, 'sample',
      '2026-09-30', repeat('a', 64), repeat('b', 64));
    raise exception 'FAIL: B attached a result to A''s scenario';
  exception when foreign_key_violation then raise notice 'PASS: B cannot attach a result to A''s scenario (FK)';
  end;

  begin
    insert into public.scenario_results (scenario_id, user_id, market_scenario, style, strategy, reinvest, result,
      engine_version, model_version, scenario_seed, data_kind, data_end, market_checksum, input_checksum)
    values (a1, a, 'x', 'broad', 'threshold', true, '{}', 'v', 'm', 1, 'sample', '2026-09-30',
      repeat('a', 64), repeat('b', 64));
    raise exception 'FAIL: B inserted a result owned by A';
  exception when insufficient_privilege then raise notice 'PASS: B cannot create a result as A (RLS)';
  end;

  begin
    update public.scenario_results set result = '{}' where true;
    raise exception 'FAIL: results are updatable';
  exception when insufficient_privilege then raise notice 'PASS: results cannot be updated by anyone (no grant)';
  end;

  begin
    update public.scenarios set user_id = a where true;
    raise exception 'FAIL: scenario owner can be changed';
  exception when insufficient_privilege then raise notice 'PASS: only the name column is updatable';
  end;

  begin
    insert into public.explainer_usage (user_id, requests) values (current_setting('test.user_b')::uuid, 0);
    raise exception 'FAIL: explainer_usage is directly writable';
  exception when insufficient_privilege then raise notice 'PASS: explainer_usage only via record_explainer_usage()';
  end;

  perform public.record_explainer_usage(100, 20);
  select count(*) into n from public.explainer_usage;
  if n <> 1 then raise exception 'FAIL: B sees % usage rows (expected only own)', n; end if;
  raise notice 'PASS: usage counter writes and shows only B''s own row';
end $$;

-- ---------------------------------------------------------------- signed out (anon): nothing at all
select set_config('request.jwt.claims', '', true);
set local role anon;

do $$
begin
  begin
    perform 1 from public.scenarios;
    raise exception 'FAIL: anon can query scenarios';
  exception when insufficient_privilege then raise notice 'PASS: anon cannot read scenarios';
  end;
  begin
    perform 1 from public.scenario_results;
    raise exception 'FAIL: anon can query results';
  exception when insufficient_privilege then raise notice 'PASS: anon cannot read results';
  end;
  begin
    perform public.save_scenario('x', '{}', null, 'x', 'broad', 'threshold', true, '{}', 'v', 'm', 1, 'sample',
      '2026-09-30', repeat('a', 64), repeat('b', 64));
    raise exception 'FAIL: anon can call save_scenario';
  exception when insufficient_privilege then raise notice 'PASS: anon cannot call save_scenario';
  end;
end $$;

-- ---------------------------------------------------------------- user A still has everything, unchanged
set local role authenticated;
select set_config('request.jwt.claims', json_build_object('sub', current_setting('test.user_a'), 'role', 'authenticated')::text, true);

do $$
begin
  if (select name from public.scenarios where id = current_setting('test.a1')::uuid) is distinct from 'A private' then
    raise exception 'FAIL: A''s scenario was changed or removed';
  end if;
  if (select count(*) from public.explainer_usage) <> 0 then
    raise exception 'FAIL: A can see B''s usage row';
  end if;
  raise notice 'PASS: A''s scenario is intact and A cannot see B''s usage';
end $$;

select 'ALL RLS CHECKS PASSED' as result;
rollback;
