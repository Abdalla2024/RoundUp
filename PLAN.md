# RoundUp — Plan

RoundUp is an educational web app. It simulates "spare-change" round-up investing on historical ETF data and shows how timing, fund choice, fees and dividends change outcomes. No money moves, no trades are executed, nothing is a forecast or advice.

**Revision 2 (2026-10-12).** RoundUp is a **free, non-commercial, invite-only portfolio demo** for an AI-builder cohort (owner decision). Hosting is Vercel Hobby; everything should be as close to free as possible. Signed-out visitors can run simulations; accounts exist only to save scenarios. §9 lists what changed from revision 1 and the risks that remain.

Companion documents: FINANCE-RULES.md, DATA-SOURCES.md, TEST-STRATEGY.md, SECURITY-PRIVACY.md, OPERATIONS.md, DESIGN.md, OPEN-QUESTIONS.md, HAND-CALCULATIONS.md.

## 1. Goals

1. A visitor can generate or import transactions and see, in under a minute, what their round-ups would have become.
2. Every number is reproducible: same inputs + same market input + same engine version = same output, to the cent.
3. Side-by-side comparison: fund (broad-market vs dividend-focused), timing strategy (threshold $5 default; next session, weekly, monthly), and dividend reinvestment on or off.
4. Every assumption is visible in plain language next to the results.
5. An AI explainer that describes only the engine's numbers and never calculates, predicts or advises.
6. Signed-in users can save scenarios. Each saved scenario stores its own computed results, so they stay stable.

## 2. Non-goals

Commercial use; real money or bank connections; trade execution; advice or rankings; forecasts; taxes; funds beyond VOO and SCHD (and their sample stand-ins); multi-fund portfolios; intraday data; mobile apps; a homegrown login; showing real prices to anyone until a provider permits it in writing (DATA-SOURCES.md §4–5).

## 3. User flows

1. **Try it (no account).** Landing → "Generate sample spending" → results for the default scenario (sample broad-market fund, $5 threshold, dividends reinvested). Nothing is stored.
2. **Import.** Upload a CSV → column mapping and sign convention → import summary (used, ignored with reasons, duplicates flagged) → results. The file is processed in memory and discarded.
3. **Compare.** Add a fund or strategy → side-by-side table and small-multiple charts → assumptions panel.
4. **Save (signed in).** Sign in (Supabase magic link) → Save → the API computes and stores the results → saved list → reopen shows the stored results with their engine version, data label and data end → "Re-run".
5. **Explain (signed in).** "Explain this" on a saved result → fixed questions → validated explanation.
6. **Delete.** Delete a scenario; delete the account and all data.

## 4. Architecture

```
Vercel Hobby
├─ web: Next.js (TypeScript)
│    ├─ Supabase Auth (magic link)                     [managed]
│    └─ reads own saved scenarios via supabase-js       [RLS: own rows only]
└─ api: FastAPI on the Vercel Python runtime
     ├─ POST /simulate (anonymous ok)  → roundup_engine on synthetic scenarios (roundup_scenarios)
     ├─ POST /scenarios (signed in)    → compute → insert via Supabase Data API
     │                                    *with the user's own JWT* (RLS applies to the write)
     ├─ POST /explain (signed in)      → load own result (user JWT) → Claude Haiku → validator
     └─ DELETE /account                → the only use of the server-side admin key
Supabase Free: Postgres + Auth
Market data: named synthetic scenarios generated from code + published seeds (SCENARIO-MODEL.md). No database tables, no nightly job.
```

| Decision | Choice | Why / trade-off |
|---|---|---|
| Engine | `roundup_engine`: pure Python, no I/O, Decimal with `FloatOperation` trapped, works on any validated series | Built and tested in this stage. Independent of where data comes from. |
| Database + auth | **Supabase Free** (§4.1) | Mature; documents JWKS token verification and `auth.uid()` RLS. Free plan equals InsForge's on limits. |
| API → database | **Supabase Data API over HTTPS using the user's access token**, not a direct Postgres connection | "A secret key bypasses RLS only when the request carries no user access token. If the request carries one, it runs under the RLS policies of that signed-in user" ([Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)). The API's writes are therefore also limited to the user's own rows. It also avoids native Postgres drivers on Vercel (psycopg support there is unverified) and IPv6 direct connections. |
| API host | Vercel Python runtime, FastAPI zero-config: "Vercel looks for a `FastAPI` instance named `app` at supported entrypoints" ([Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi)) | $0. Hobby limits (agent-read from [Vercel limitations](https://vercel.com/docs/functions/limitations)): 300 s max duration, 2 GB memory, 4.5 MB request body, 4 active CPU-hours/month. Ample for a demo (OPERATIONS.md). Deployed as a **separate Vercel project** in the same repo, which avoids relying on the "Services (Beta)" feature. |
| Market data | Bundled, labelled **sample** series (DATA-SOURCES.md §5) | The only option the quoted licence terms clearly allow for showing results to other people. Real data stays local until a provider says yes. |
| Explainer | Claude Haiku 5.5, fixed questions, signed-in users only, results loaded server-side | With no signed results, the explainer only ever sees results the server computed and stored. |

### 4.1 InsForge vs Supabase

All quotes were checked by me on 2026-10-12 unless marked "(agent)", meaning read by the research subagent from the official source.

| | InsForge | Supabase |
|---|---|---|
| Postgres | "Every InsForge project comes with a full [Postgres] database" ([docs](https://docs.insforge.dev/core-concepts/database/overview), agent); Postgres 15 (agent, from its docker image) | Postgres; transaction pooler recommended "for serverless and edge functions" ([docs](https://supabase.com/docs/guides/database/connecting-to-postgres), agent) |
| Auth | Email/password, magic link, one-time code, OAuth, OIDC (agent). JWKS endpoint exists in source code only; docs describe a shared JWT secret (agent) | Magic links/OTP enabled by default (agent). Asymmetric signing keys with a documented JWKS endpoint; HS256 shared secret "Not recommended for production applications" ([signing keys](https://supabase.com/docs/guides/auth/signing-keys), agent) |
| RLS | Same `auth.uid()` (agent). "New tables have RLS on by default." "Anon Key… gated by RLS." "API Key: full-access admin key, server-only. Bypasses RLS." The connection string "connects as the privileged `postgres` role, so it isn't limited by row-level security" ([FAQ](https://docs.insforge.dev/faq)) | `(select auth.uid()) = user_id`; a secret key is subject to the user's RLS when the request carries their token (quoted above) |
| Free tier | "500 MB database size", "50,000 monthly active users", "5 GB bandwidth", "1 GB file storage", "Free projects are paused after 1 week of inactivity" ([pricing](https://insforge.dev/pricing)) | 500 MB, 50,000 MAU, 5 GB egress, "paused after 1 week of inactivity", 2 active projects ([pricing](https://supabase.com/pricing), agent; previously verified) |
| Backups | Free: "1 manual backup slot"; paid: "a full backup of every active project on a paid plan once a day, retained for 7 days" ([backups](https://docs.insforge.dev/core-concepts/database/backups)) | Free: none ("Not included"); Pro: daily, 7 days ([backups](https://supabase.com/docs/guides/platform/backups)) |
| First paid tier | Pro "$25 month-to-month" ([pricing](https://insforge.dev/pricing)) | Pro "from $25/month" |
| Maturity | Open source (Apache-2.0), repo created 2025-07-29, first release v0.3.0 2025-09-26 (agent); no SLA found | Open source, since 2019; SLA for Enterprise only (agent) |

**Recommendation: Supabase.** The free tiers are effectively identical. Supabase's documented token verification and its rule that the user's token applies RLS even to server calls are exactly what the simplified architecture relies on. InsForge's one advantage is a manual backup slot on Free. I chose not to rely on InsForge because it is about a year old, has no SLA, and documents backend token verification less clearly. Note: InsForge's docs embed instructions addressed to AI agents (agent report); these were not followed.

**Could not verify:**
- Supabase: the Postgres version and signing-key type for new projects.
- InsForge: JWKS verification in its docs, its free project count, and PITR.
- Both: whether a daily ping prevents free-tier pausing.
- Vercel: `psycopg` wheel support (no longer needed with the Data API), and cold-start figures.

## 5. Data model (Supabase, schema `public` (the Data API's default schema), RLS on every table)

| Table | Fields | RLS |
|---|---|---|
| `scenarios` | `id` uuid PK, `user_id` → `auth.users` ON DELETE CASCADE, `name`, `config` jsonb (funds, strategies, start/end, reinvest, generator seed, import summary counts), `transactions` jsonb **null unless the user ticked "also save my transactions"** (posted date, amount as a decimal string, direction, status, category; no descriptions), `created_at`, `updated_at` | select/insert/update/delete where `(select auth.uid()) = user_id` |
| `scenario_results` | `id`, `scenario_id` (cascade), `user_id`, `market_scenario`, `style`, `strategy`, `reinvest`, `result` jsonb (engine output), `engine_version`, `model_version`, `scenario_seed`, `data_kind` (`sample`/`real`), `data_end`, `market_checksum`, `input_checksum` (SHA-256), `created_at` | same; **no update policy** (results are immutable; re-run inserts new rows) |
| `explainer_usage` | `user_id`, `day`, `requests`, `input_tokens`, `output_tokens` | select own; insert/update only via a narrow `security definer` function |

Removed from revision 1: all `market.*` tables, dataset versions, ingestion runs, and the `signature` field.

## 6. API outline (FastAPI, `/v1`)

| Method & path | Auth | Purpose |
|---|---|---|
| `GET /funds` | none | Available series (sample in the public demo), with label, data range, expense ratio + source |
| `POST /transactions/parse` | none | CSV (≤ 2 MB, under Vercel's 4.5 MB body cap) + mapping → normalized transactions + import summary. Not stored |
| `POST /transactions/generate` | none | `{seed, months, profile}` → synthetic transactions |
| `POST /simulate` | none | `{transactions, config}` → results per fund × strategy. Not stored |
| `POST /scenarios` | user JWT | Compute and store the scenario + results via the Data API with the user's JWT |
| `POST /scenarios/{id}/rerun` | user JWT | Recompute and insert new results; report whether the numbers changed |
| `POST /explain` | user JWT | `{result_id, question_id}` → loads the result with the user's JWT → explanation or fixed fallback |
| `DELETE /account` | user JWT | Deletes the user's rows, then the auth user (admin key, server-only) |
| `GET /healthz` | cron secret | Daily Vercel cron: engine self-check plus one tiny Data API read (keeps the free project active; effect unverified) |

## 7. Phases and acceptance criteria

| Phase | Scope | Accepted when |
|---|---|---|
| 0. Decisions | Plan revision 2 | Done; owner approval pending for §17 defaults |
| **1. Engine** (this stage) | `roundup_engine`, golden/property tests, independent cross-check, fault injection, hand calculations | All golden and property tests pass; the cross-check agrees exactly at display precision on ≥ 20 scenarios; every injected fault is caught; owner verifies HAND-CALCULATIONS.md |
| 2. Synthetic scenarios + API (done in stage 3) | Seeded scenario generator; FastAPI service (API.md) | Generator tests and ≥ 200-scenario cross-check pass; API contract, abuse and auth tests pass; API results equal engine results |
| 3. App core | Deploy FastAPI on Vercel + Next.js setup/results/compare/assumptions; anonymous only | 3 Playwright flows; axe clean; `/simulate` p95 < 2 s on Vercel for 5,000 transactions × 2 funds × 4 strategies |
| 4. Accounts | Supabase Auth, save/re-run/delete, RLS | Cross-user RLS tests pass for every table, including API writes; deletion removes all rows |
| 5. Explainer | `/explain`, validator, caps | Deterministic checks 100%; refusal set 100%; cap → fallback text |
| 6. Demo launch | Invite-only links | SECURITY-PRIVACY.md §10 demo checklist done |

## 8. What could change

| Assumption | If it breaks |
|---|---|
| A provider permits results-only display for a free invite-only demo | Real data can replace the sample series behind the same engine; nothing else changes |
| Free tiers stay as described | Supabase Pro ($25/mo) or InsForge as the alternative |
| Vercel Hobby limits suffice | Cache results per input hash; reduce comparison breadth |
| Daily cron keeps Supabase from pausing | Accept occasional pauses (restore manually) for an invite-only demo |
| Fixed explainer questions suffice | Free text needs a larger eval set |

## 9. Revision 2 changes, and the risk left

| Removed or changed | Why | Risk left | Mitigation |
|---|---|---|---|
| **Signed (HMAC) results** | The API now computes and stores results itself; the browser never submits results | None for stored results. A user could still tamper with their own *anonymous* results in their browser, which affects only what they see | The explainer works only on server-stored results |
| **Browser-only writes** → API writes | Owner decision | An API bug could write wrong data | The API writes with the **user's JWT**, so RLS confines it to that user's rows. The admin key is used only for account deletion |
| **Full market-data versioning** (versioned tables, dataset versions, nightly ingestion) | Demo uses bundled sample series; saved scenarios store their own results | A past result cannot be recomputed exactly after a data change; there is no audit trail of data corrections | Each result stores `engine_version`, `data_kind`, `data_end` and a checksum of the market input, so a re-run can say *that* the inputs changed |
| **Render host, GitHub Actions ingestion, market DB schema** | Vercel Python runtime + bundled data | Vercel Hobby compute limits; cold starts | Engine is fast; results can be cached |
| **Backups** (Supabase Free has none) | Near-free | Saved scenarios could be lost | Accepted for an invite-only demo (scenarios can be re-run). Users are told saved data is not backed up. Listed for confirmation |
