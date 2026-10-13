-- RoundUp schema (PLAN.md §5). Run once in the Supabase SQL editor, before 0002_rls.sql.
-- Tables live in `public`, the schema the Supabase Data API exposes by default.

create table public.scenarios (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users (id) on delete cascade,
  name          text not null check (char_length(name) between 1 and 80),
  config        jsonb not null,
  transactions  jsonb,                       -- null unless the user chose to save them; never descriptions (D-8)
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (id, user_id)                         -- target of the composite foreign key below
);

create table public.scenario_results (
  id               uuid primary key default gen_random_uuid(),
  scenario_id      uuid not null,
  user_id          uuid not null references auth.users (id) on delete cascade,
  market_scenario  text not null check (char_length(market_scenario) <= 64),
  style            text not null check (style in ('broad', 'dividend')),
  strategy         text not null check (strategy in ('threshold', 'next_session', 'weekly', 'monthly')),
  reinvest         boolean not null,
  result           jsonb not null,
  engine_version   text not null,
  model_version    text not null,
  scenario_seed    integer not null,
  data_kind        text not null check (data_kind in ('sample', 'real')),
  data_end         date not null,
  market_checksum  text not null check (market_checksum ~ '^[0-9a-f]{64}$'),
  input_checksum   text not null check (input_checksum ~ '^[0-9a-f]{64}$'),
  created_at       timestamptz not null default now(),
  -- A result can only point at a scenario owned by the same user. Foreign-key checks bypass RLS, so this
  -- constraint (not a policy) is what stops attaching a result to someone else's scenario id.
  foreign key (scenario_id, user_id) references public.scenarios (id, user_id) on delete cascade
);

create table public.explainer_usage (
  user_id        uuid not null references auth.users (id) on delete cascade,
  day            date not null default current_date,
  requests       integer not null default 0 check (requests >= 0),
  input_tokens   integer not null default 0 check (input_tokens >= 0),
  output_tokens  integer not null default 0 check (output_tokens >= 0),
  primary key (user_id, day)
);

create index scenarios_user_id_idx on public.scenarios (user_id);
create index scenario_results_scenario_id_idx on public.scenario_results (scenario_id);
create index scenario_results_user_id_idx on public.scenario_results (user_id);

create function public.touch_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.updated_at := now();
  return new;
end $$;

create trigger scenarios_touch before update on public.scenarios
for each row execute function public.touch_updated_at();
