# RoundUp — Plan

RoundUp is an educational web app. It simulates "spare-change" round-up investing on real historical ETF data and shows how timing, fund choice, fees and dividends change outcomes. No money moves, no trades are executed, nothing is a forecast or advice.

Companion documents: FINANCE-RULES.md (the rules), DATA-SOURCES.md (data and licences), TEST-STRATEGY.md, SECURITY-PRIVACY.md, OPERATIONS.md, DESIGN.md, OPEN-QUESTIONS.md.

## 1. Goals

1. A user can generate or import transactions and see, in under a minute, what their round-ups would have become in a real ETF since 2012.
2. Every number is reproducible: same inputs + same dataset version + same engine version = same output, to the cent.
3. Side-by-side comparison of the things the user can change: fund (broad-market vs dividend-focused), timing strategy (next session / weekly / monthly / threshold), and dividend reinvestment on or off.
4. Every assumption is visible in plain language next to the results.
5. An AI explainer that describes only the engine's numbers and never calculates, predicts or advises.
6. Accounts let users save scenarios. Uploaded transactions are not stored unless the user chooses.

## 2. Non-goals (v1)

Real money, brokerage or bank connections (no Plaid); trade execution; advice, recommendations or "best fund" rankings; forecasts or projections; taxes; funds beyond the first two (plus their alternates); multi-fund portfolios or rebalancing; intraday data; mobile apps; social or sharing features; a homegrown login.

## 3. User flows

1. **Try it (no account).** Landing → "Generate sample transactions" (choose a spending profile and period) → results for the default scenario: one broad-market fund, next session, reinvest on. Whether anonymous use is allowed is OPEN (it affects data licensing).
2. **Import.** Upload CSV → column mapping and sign convention (R-1.3) → import summary (accepted, ignored with reasons, duplicates flagged) → results. The file is processed in memory and discarded.
3. **Compare.** From results → add a fund or strategy → side-by-side table and chart → assumptions panel.
4. **Explain.** On any result → "Explain this" buttons (fixed questions in v1) → plain-language explanation built only from that result.
5. **Save.** Sign in (managed auth) → save scenario (configuration; transactions only if the user ticks "also save my transactions") → saved scenarios list → reopen shows stored results with their "as of" date and dataset version → "Re-run with latest data".
6. **Delete.** Delete a scenario; delete the account and all data (immediate, irreversible, confirmed).

## 4. Architecture

```
Browser (Next.js on Vercel)
  ├─ Supabase Auth (sign-in, sessions)          [managed]
  ├─ Supabase Postgres via supabase-js          [RLS: own scenarios/runs only]
  └─ FastAPI (small host) with the user's access token
        ├─ parse CSV / generate transactions    [in memory, nothing stored]
        ├─ simulate  → roundup_engine (pure Python library, Decimal)
        │                reads market data (read-only DB role)
        │                returns result + HMAC signature
        ├─ explain   → verifies signature → Claude API → output validator
        └─ delete account (server-only admin key)
Nightly job (GitHub Actions cron)
  └─ roundup_data: provider adapter → checks → new dataset version → publish
```

Key decisions:

| Decision | Choice | Why / trade-off |
|---|---|---|
| Engine | Standalone Python package `roundup_engine`, no I/O, no framework imports, Decimal with `FloatOperation` trapped | Testable in isolation and reusable by the cross-check. Cost: data must be passed in explicitly. |
| Hosted DB + auth | **Supabase** (Postgres + Auth in one, RLS with `auth.uid()`) | One vendor for auth and data. RLS is documented with `(select auth.uid()) = user_id` ([Supabase RLS docs](https://supabase.com/docs/guides/database/postgres/row-level-security)). Neon is a good database but would need a separate auth vendor. |
| Who writes user data | **The browser, through Supabase with RLS.** FastAPI has **no** write access to user tables; it holds a read-only role for market data, plus the admin key only for account deletion | A bug in the API cannot leak or overwrite another user's scenarios. Results the browser saves are signed by the API, so the explainer can trust them. |
| API host | Render Starter ($7/mo, always-on). Fly.io is the alternative at about $2.19 per 30 days for 256 MB | Simplest always-on Python host. Free tiers sleep after 15 minutes idle (Render) or no longer exist for new organizations (Fly). See OPERATIONS.md. |
| Frontend host | Vercel. Hobby only while the project is non-commercial ("the Hobby plan restricts users to non-commercial, personal use only", [Vercel docs](https://vercel.com/docs/plans/hobby)); Pro ($20/mo) before any monetization | Brief. Whether a free educational site counts as "commercial" is OPEN. |
| Nightly job | GitHub Actions `schedule` in a **private** repo | Free minutes are enough (job ~2–5 min/night). Caveat: scheduled runs "can be delayed during periods of high loads". Freshness monitoring covers that. |
| Market data | Provider behind an adapter (DATA-SOURCES.md §5). Conditional recommendation: EODHD; runner-up: Tiingo | Licence for public display not yet confirmed (OPEN). |
| Explainer model | Claude Haiku 5.5 (`claude-haiku-5-5`), fixed questions in v1 | Cheapest current model ($0.10 / $0.50 per MTok in/out, prompts ≤100k tokens, [pricing](https://platform.claude.com/docs/en/about-claude/pricing)). The task is narrow; output is validated anyway. Sonnet 5.5 can be evaluated if quality falls short. |

## 5. Data model

Postgres `numeric` for all money, prices and shares (exact). It maps to Python `Decimal`.

**Schema `market`** (readable by all authenticated and anonymous roles; writable only by the ingestion role):

| Table | Fields |
|---|---|
| `funds` | `symbol` PK, `name`, `issuer`, `category` (broad/dividend), `inception_date`, `expense_ratio` numeric, `expense_ratio_as_of`, `expense_ratio_source_url` |
| `dataset_versions` | `id` PK, `created_at`, `provider`, `status` (staging/published/rejected), `data_end` date, `checksum`, `notes` |
| `prices` | `symbol`, `day`, `close` numeric(18,6), `valid_from_version`, `valid_to_version` (null = current), `source`. PK (`symbol`, `day`, `valid_from_version`) |
| `dividends` | `symbol`, `ex_date`, `pay_date` (nullable), `amount_raw` numeric(18,8), `kind`, version fields, `source` |
| `splits` | `symbol`, `ex_date`, `ratio` numeric, version fields, `source` |
| `adjusted_closes` | `symbol`, `day`, `adj_close`, version fields (cross-check only, R-7.7) |
| `ingestion_runs` | `id`, `started_at`, `finished_at`, `status`, `checks` jsonb, `dataset_version_id` |

The version fields mean a provider correction never overwrites a row. The old row is closed (`valid_to_version`) and a new one is opened. Any dataset version can be rebuilt (R-12.4).

**Schema `app`** (RLS on every table: `user_id = (select auth.uid())`):

| Table | Fields |
|---|---|
| `scenarios` | `id` uuid PK, `user_id` → `auth.users` ON DELETE CASCADE, `name`, `config` jsonb (funds, strategies, threshold, start/end, reinvest, generator seed, import summary counts), `created_at`, `updated_at` |
| `scenario_transactions` | only if the user opts in: `id`, `scenario_id` (cascade), `user_id`, `day`, `amount_cents` bigint, `direction`, `category`. **No merchant description by default.** Storing descriptions is OPEN |
| `scenario_runs` | `id`, `scenario_id` (cascade), `user_id`, `dataset_version_id`, `engine_version`, `created_at`, `result` jsonb, `signature` |
| `explainer_usage` | `user_id`, `day`, `requests`, `input_tokens`, `output_tokens` (written by the API through a narrow security-definer function, used for per-user caps) |

## 6. API outline (FastAPI, `/v1`)

| Method & path | Auth | Purpose |
|---|---|---|
| `GET /funds` | none | Funds, coverage start, data end, expense ratio + source |
| `GET /market/status` | none | Latest published dataset version, data end, last ingestion status |
| `POST /transactions/parse` | optional | Multipart CSV (≤ 2 MB, ≤ 20,000 rows) + mapping → normalized transactions + import summary. Not stored |
| `POST /transactions/generate` | optional | `{seed, months, profile}` → synthetic transactions |
| `POST /simulate` | optional | `{transactions, config}` → per-fund × per-strategy results, daily series, flags, `dataset_version`, `engine_version`, HMAC `signature` |
| `POST /explain` | required (OPEN: allow anonymous?) | `{result, signature, question_id}` → validated explanation or fixed fallback text. Rate- and spend-capped |
| `DELETE /account` | required | Deletes the user's rows and the auth user (admin API, server-only) |
| `GET /healthz` | none | Liveness + DB reachability + data freshness |

Scenario and run CRUD go browser → Supabase directly (RLS).

## 7. Phases and acceptance criteria

| Phase | Scope | Accepted when |
|---|---|---|
| **0. Decisions** (this) | Planning docs; licence emails sent | You approve the plan; OPEN items that block Phase 1 are decided (OPEN-QUESTIONS.md marks which ones) |
| **1. Engine** | `roundup_engine` + synthetic fixtures + golden, property and cross-check tests | Every non-OPEN rule has ≥1 golden case; all property tests pass at 5,000 examples; the independent `Fraction` implementation agrees exactly at display precision; the `FloatOperation` trap is on; no I/O in the package |
| **2. Data** | Adapter for the chosen provider (development plan only, private), ingestion, checks, versioning, backfill 2012 →, nightly job | Backfill for all candidate funds passes every check; the VOO 2013 and SCHD 2024 split cases pass; the adjusted-close cross-check passes within the decided tolerance; 7 consecutive green nightly runs; a deliberately corrupted fixture is caught |
| **3. App core** | FastAPI endpoints; Next.js screens: setup, results, comparison, assumptions; no accounts | 3 Playwright flows pass (generate → results, import → results, compare); axe shows no serious/critical issues; `/simulate` p95 < 2 s for 5,000 transactions × 2 funds × 4 strategies on the chosen host |
| **4. Accounts** | Supabase Auth, saved scenarios, opt-in transaction saving, deletion | RLS cross-user tests pass for every table; the service key is absent from the client bundle; account deletion removes every row (verified by test) |
| **5. Explainer** | `/explain`, validator, caps | Deterministic checks 100% on the eval set; advice/prediction refusal set 100%; spend cap verified by test (cap hit → fallback text, no error page) |
| **6. Launch readiness** | Licence signed; legal review of disclaimer, privacy policy and terms; monitoring; backups | Every launch blocker in SECURITY-PRIVACY.md §10 and OPEN-QUESTIONS.md is closed; restore-from-backup drill done once |

Nothing is publicly visible before Phase 6. Phases 1–5 run on private or protected deployments.

## 8. What could change

| Assumption | What changes if it breaks |
|---|---|
| A display licence is affordable from EODHD or Tiingo | Phase 2 provider choice; possibly a smaller public feature set (e.g. charts of derived values only) or a closed beta |
| The provider supplies pay dates | If not, R-8.8 must be decided (and disclosed) before Phase 1 is complete |
| Free educational use is "non-commercial" for Vercel and data licences | Plan costs rise (Vercel Pro, commercial licences) |
| Anonymous users may run simulations | If not, the "Try it" flow requires sign-in |
| Haiku 5.5 is good enough for explanations | Switch to Sonnet 5.5: about 20× per-token cost (OPERATIONS.md) |
| Supabase Free is enough during development | Pro ($25/mo) before launch is already assumed, because Free has no automatic backups and pauses after 1 week of inactivity |
| Fixed explainer questions are enough | Free-text questions would need a bigger eval set and a higher spend cap |
