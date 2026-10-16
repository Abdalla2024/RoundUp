# RoundUp — Operations

**Revision 2 (2026-10-12): near-free invite-only demo.** Prices were read from official pages on 2026-10-12. They exclude tax and change often.

## 1. Cost estimate (per month)

| Item | Plan | Cost | Source / note |
|---|---|---|---|
| Frontend + API | Vercel **Hobby** (two projects: web, api) | **$0** | Hobby is "non-commercial, personal use only" ([Vercel](https://vercel.com/docs/plans/hobby)); a free portfolio demo fits. Included: 4 active CPU-hours, 1,000,000 function invocations, 100 GB fast data transfer per month |
| Database + auth | Supabase **Free** | **$0** | 500 MB DB, 50,000 MAU; pauses after 1 week of inactivity; no backups ([pricing](https://supabase.com/pricing)) |
| Market data, shared demo | Bundled sample series | **$0** | DATA-SOURCES.md §5 |
| Market data, local real mode (optional) | EODHD personal | $19.99 for one month, **optional** | Developer-only; never shown to others ([pricing](https://eodhd.com/pricing)) |
| Keep-alive and scheduled tasks | Vercel Cron (Hobby: once per day) | $0 | [Vercel cron limits](https://vercel.com/docs/cron-jobs/usage-and-pricing) (agent-read) |
| CI | GitHub Actions | $0 | Free minutes are enough for tests |
| Errors / uptime | Sentry Developer, UptimeRobot Free | $0 | Optional for a demo |
| AI explainer | Claude Haiku 5.5, capped | **≤ $5** (hard cap) | §2–3 |
| **Total** | | **$0–5/month** (+ optional $19.99 once) | |

**Stage 3 cost impact: none.** The API runs on the same Vercel Hobby project budget, the scenarios are generated from code (no storage), and no paid service was added. Measured cost per request locally: ≈ 0.15 CPU-seconds for a full-range simulation, so 4 active CPU-hours ≈ 96,000 such requests a month. Responses are large (≈ 0.7–1 MB for a full-range run with its daily series), which counts against the 100 GB transfer allowance: ≈ 100,000 full-range responses a month.

**Stage 5 cost impact: none.** No paid service was added and there is no AI key yet. Measured locally on 2026-10-13 (`web/screenshots/perf-report.json`, production build, Chrome):

| Measure | Result |
|---|---|
| Setup page first load | 613,518 bytes uncompressed, **201,734 bytes transferred**, 594 ms |
| Run a full-range simulation through to the results page | +1,015,314 bytes uncompressed (Recharts is loaded only now), **174,284 transferred**, 727 ms |
| `POST /v1/simulate`, 2015–2024, `buys: "none"` (what the site sends) | **59,313 bytes**, 147 ms, 770 chart points |
| Same with `buys: "all"` | 553,448 bytes (why the site asks for `none`) |
| `POST /v1/compare`, same range | 118,384 bytes, 249 ms |

Transferred bytes vary between runs (a repeat run on the same day gave 148,132 for the setup page and 178,232 for the run; uncompressed sizes were identical), so treat them as ≈ 150–200 KB. At ≈ 60 KB per run, the 100 GB Hobby transfer allowance is about 1.7 million simulations a month. Timings are on a laptop, not Vercel (not verified there).

**Compute budget check.** Hobby includes 4 active CPU-hours (14,400 CPU-seconds) a month. The engine runs one fund × strategy over ~3,700 calendar-open days (2012 → 2026). Phase 3 will measure the actual cost per run on Vercel. If one full comparison (2 funds × 4 strategies) costs ≤ 1 CPU-second, the allowance covers ≥ 14,000 comparisons a month, far beyond an invite-only cohort. Exceeding it pauses the feature for up to 30 days ([Hobby docs](https://vercel.com/docs/plans/hobby)), so the API caches results by input hash.

## 2. AI cost per request

Assumptions:
- Input: ~3,000 tokens (system prompt + one result).
- Output: ≤ 350 tokens.
- At most one retry.

| Model | Price (input / output per MTok) | Per explanation | Worst case with retry |
|---|---|---|---|
| Haiku 5.5 (`claude-haiku-5-5`), prompts ≤ 100k tokens | $0.10 / $0.50 | **$0.000475** | $0.00095 |
| Sonnet 5.5 (`claude-sonnet-5-5`) | $2 / $10 | $0.0095 | $0.019 |

Prices verified on the [pricing page](https://platform.claude.com/docs/en/about-claude/pricing). At the worst case, the **$5 cap buys ≈ 5,200 Haiku explanations a month**. Identical requests (same result + question) are served from a cache.

## 3. AI spend cap

1. **Anthropic workspace limit: $5/month** on a dedicated workspace. Limits can be set "lower than (but not higher than) your organization's limits", and "You cannot set limits on the Default Workspace" ([workspaces](https://platform.claude.com/docs/en/manage-claude/workspaces), agent-read in revision 1).
2. **App budget:** $0.25/day computed from `explainer_usage`. Explainer access is limited to signed-in users, 20 explanations a day each.
3. **Fallback:** when any cap or the validator stops a call, a fixed non-AI template filled with engine numbers is shown. There is never an error page.

## 4. Logging

- **API:** structured JSON lines to Vercel runtime logs (Hobby keeps 1 hour). Logged: route, status, latency, request id, engine version, user id hash.
- **Never logged:** request or response bodies, CSV content, transactions, tokens.
- **Explainer:** question id, token counts, validator verdict, model id. No prompt text.

## 5. Monitoring and alerts (demo scale)

| Signal | How | Alert |
|---|---|---|
| Site and API up | UptimeRobot (free, 5-minute checks) on `/` and `/v1/healthz` | email after 2 failures |
| Supabase paused | Daily Vercel cron calls `/v1/healthz`, which makes one tiny Data API read. Whether this prevents pausing is **unverified**. | The cron fails → Vercel shows a failed cron; the uptime monitor catches the API error |
| API errors | Sentry free (optional) | new issue |
| AI spend | Anthropic workspace limit + app counter | at the cap (fallback engages automatically) |
| Hobby usage | Vercel usage page | checked weekly during the demo |

## 5a. Detecting failed or slow API requests

| Signal | Where it comes from | How it is noticed |
|---|---|---|
| **Every request** | One JSON log line per request in Vercel runtime logs: `request_id`, `route`, `status`, `latency_ms`, `slow`, `error_code`, salted client hash. No bodies, IPs, amounts or descriptions. | Filter the Vercel logs by `status >= 500`, `slow: true`, or `error_code`. Hobby keeps logs for 1 hour, so check soon after testing. |
| **Failed request (5xx)** | The error handler always returns `INTERNAL` or `STORAGE_UNAVAILABLE` with an `X-Request-ID`; the log line has the same id. | A user can quote the request id. Sentry free (optional) alerts on new server errors. |
| **Slow request** | `latency_ms ≥ 2000` sets `slow: true`. Every response also has a `Server-Timing: app;dur=<ms>` header, visible in browser dev tools. | Filter on `slow: true`. Measured locally: full-range simulate ≈ 144 ms and compare ≈ 272 ms median (2012–2026, about 8,000 generated purchases), so a slow line means something is wrong. |
| **API down or engine broken** | `GET /v1/health` runs a tiny engine self-check (the G-11 case) and returns 503 `degraded` if it fails. | UptimeRobot (free, 5-minute checks) on `/v1/health`, emailing after 2 failures. |
| **Abuse** | 429 `RATE_LIMITED` responses in the logs. | Many 429s from one client hash suggest abuse. Rate limits are per server instance (Vercel may run several), so they slow abuse rather than stop it. Vercel's WAF custom rules (Hobby: up to 3) are the next step if needed. |

## 6. Backups and recovery

- **Supabase Free has no backups.** The owner accepted this risk for the invite-only demo (listed for confirmation). The only user data is saved scenarios, which can be re-run. Users are told.
- Everything else is reproducible from git: code, migrations, sample series (generated from a committed seed), and the engine version.
- If saved data must be protected later: move to Supabase Pro (daily backups, 7 days) or InsForge (Free includes 1 manual backup slot).

## 7. Incidents

**Data-provider outage.** Not applicable to the shared demo: the sample series are bundled with the API. In local real mode, a failed fetch shows an error, and nothing is cached beyond what the provider's terms allow.

**Wrong price or event in a sample or real series.**
1. Engine validation (R-6, R-7.5, R-8.7, R-8.8) rejects structurally wrong data before any run.
2. For plausible-but-wrong values, fix the series or the generator and add a golden case.
3. Saved results stay as stored (R-12.4). "Re-run" recomputes them and tells the user if the numbers changed, using the stored market checksum.

**Engine bug.** Every stored result carries `engine_version`. Fix the bug, add a golden case, bump the version, and show "Re-run to update" on results from affected versions.

**Supabase project paused.** Restore it from the dashboard (InsForge documents restoring paused projects for up to 30 days; Supabase's restore window is unverified). Anonymous simulations keep working throughout, because they don't touch the database.

## 8. Working copy location (2026-10-16)
The working copy lives in `~/Desktop`, which iCloud syncs. The sync creates conflict copies named `name 2.ext` and `name 3.ext` (seen: fixtures, screenshots, `.next/types`, test output), and twice they were committed by accident. Decision (owner): move the repository folder out of Desktop (for example `~/code/RoundUp`). Until then `.gitignore` ignores `* 2.*`, `* 3.*` and `* 4.*` so a duplicate cannot be committed, and a stray `.next/types/... 2.ts` makes `tsc` fail ("Duplicate identifier"): delete `web/.next` and retry. After the move, `tools/run-e2e-linux.sh` and the CI emulation still work (they use `~/.cache`).
