-- LOCAL TESTING ONLY. Mimics the parts of a Supabase project the migrations rely on, so the SQL can be tested
-- against plain Postgres. Never run this on Supabase.
do $$ begin                                               -- roles are cluster-wide: create once
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then create role service_role nologin bypassrls; end if;
end $$;
grant anon, authenticated, service_role to current_user;   -- allow SET ROLE from the test session (like `postgres`)
create schema auth;
create table auth.users (id uuid primary key, email text);
-- auth.uid() as defined by Supabase Auth (github.com/supabase/auth, migrations/20220224000811_update_auth_functions)
create function auth.uid() returns uuid language sql stable as $$
  select coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;
grant usage on schema auth to anon, authenticated, service_role;
grant execute on function auth.uid() to anon, authenticated, service_role;
grant usage on schema public to anon, authenticated, service_role;
-- The default grants the RLS migration must revoke ("projects that still grant anon and authenticated by default").
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public grant all on functions to anon, authenticated, service_role;
insert into auth.users (id, email) values
  ('00000000-0000-0000-0000-00000000000a', 'a@example.test'),
  ('00000000-0000-0000-0000-00000000000b', 'b@example.test');
