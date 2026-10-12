# RoundUp — Operations

Prices were read from official pricing pages on 2026-10-12 (sources in DATA-SOURCES.md, PLAN.md, and below). They exclude tax and change often, so re-check them before committing.

## 1. Cost estimate (per month)

| Item | Development (Phases 1–5, private) | Launch (small public site) | Source |
|---|---|---|---|
| Frontend: Vercel | $0 (Hobby) | $0 Hobby *if* non-commercial (OPEN); otherwise Pro "$20/mo." | [vercel.com/pricing](https://vercel.com/pricing), [Hobby docs](https://vercel.com/docs/plans/hobby) |
| DB + auth: Supabase | $0 (Free: 500 MB DB, 50,000 MAU; no automatic backups; "paused after 1 week of inactivity") | Pro "From $25/month" (daily backups, 7 days) | [supabase.com/pricing](https://supabase.com/pricing) |
| API host: Render | $0 on Free (sleeps after 15 minutes idle; fine for development) | Starter "$7/month" (512 MB, always on) | [render.com/pricing](https://render.com/pricing) |
| Nightly job: GitHub Actions (private repo) | $0 (2,000 free minutes; we use ~150) | $0 | [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) |
| Market data | EODHD personal $19.99 (private use; confirm it covers development) **or** Tiingo Power $30 | **Tiingo display licence $250 (UNVERIFIED)** or **EODHD Custom "from $399.00/mo"** (by quote) | DATA-SOURCES.md |
| Error monitoring: Sentry | $0 (Developer: 1 user, 5k errors, 1 cron monitor) | $0 | [sentry.io/pricing](https://sentry.io/pricing/) |
| Uptime: UptimeRobot | $0 (50 monitors, 5-minute interval) | $0 | [uptimerobot.com/pricing](https://uptimerobot.com/pricing/) |
| AI explainer (Claude Haiku 5.5) | < $5 (evals) | ~$5 per 10,000 explanations (see §2), capped | [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| **Total** | **≈ $20–35** | **≈ $282–451 + AI** (more if the EODHD quote exceeds $399) | |

**Data licensing is roughly 85–90% of launch cost.** The cost is driven by whether a cheaper display arrangement exists (e.g. an educational or academic licence) and by OPEN question OQ-1. Hosting is under $60/mo even on paid plans. A domain name is not included (price not researched).

## 2. AI cost per request

Assumptions per explanation:
- **Input:** system prompt and rules ~1,500 tokens + signed result JSON ~1,500 tokens = ~3,000 tokens.
- **Output:** ≤ 350 tokens (`max_tokens` = 500).
- **Retries:** at most one retry if the validator rejects the output.

| Model | Input price | Output price | Cost per explanation | ×2 worst case (retry) | Per 10,000 |
|---|---|---|---|---|---|
| Haiku 5.5 (`claude-haiku-5-5`) | $0.10 / MTok (prompts ≤ 100k tokens) | $0.50 / MTok | 3,000 × 0.10e-6 + 350 × 0.50e-6 = **$0.000475** | $0.00095 | **≈ $4.75** |
| Sonnet 5.5 (`claude-sonnet-5-5`) | $2 / MTok | $10 / MTok | 3,000 × 2e-6 + 350 × 10e-6 = **$0.0095** | $0.019 | ≈ $95 |

Prices were verified on the [pricing page](https://platform.claude.com/docs/en/about-claude/pricing). Cost reductions:
- **Prompt caching** of the fixed system prompt (cache hits on Haiku 5.5: $0.01 / MTok).
- **Response caching:** explanations are deterministic inputs (result hash + question id), so identical requests are served from our cache, not the model.

## 3. AI spend cap

Layered, with the cheapest check first:

1. **Anthropic workspace limit.** A dedicated workspace holds the explainer key, with a monthly spend limit of **$25** at launch. Anthropic docs: workspace limits can be set "lower than (but not higher than) your organization's limits", and "You cannot set limits on the Default Workspace", which is why the explainer gets its own workspace. Over the limit, the API returns HTTP 400 ("You have reached your specified workspace API usage limits") ([workspaces](https://platform.claude.com/docs/en/manage-claude/workspaces), [rate limits](https://platform.claude.com/docs/en/api/rate-limits)).
2. **App global budget.** The API sums the estimated cost from `explainer_usage` and stops calling the model at **$1/day**.
3. **Per-user limits:** 20 explanations a day per signed-in user. Anonymous users: OPEN (proposed 0).
4. **Graceful fallback.** When any cap or the validator stops a call, a fixed, non-AI explanation template filled with engine numbers is shown. There is never an error page.
5. **Alerts** at 50%, 80% and 100% of the monthly cap.

## 4. Logging

- Structured JSON logs from the API: request id, route, status, latency, user id hash, dataset version, engine version.
- **Never logged:** request or response bodies, CSV content, transactions, tokens or keys.
- Explainer logs: question id, token counts, validator verdict, model id. No prompt text.
- Ingestion logs: run id, provider, rows fetched, each check's result, dataset version published or rejected.
- Retention: 30 days for app logs (host limits permitting); 1 year for ingestion run records (they are small and in the DB).

## 5. Monitoring and alerts

| Signal | Tool | Alert when |
|---|---|---|
| Site and `/healthz` up | UptimeRobot (5 min) | 2 consecutive failures |
| API errors | Sentry | New issue, or error rate > 2% over 15 minutes |
| Nightly job ran | Sentry cron monitor (heartbeat) | No check-in by 08:00 UTC |
| Ingestion check failed or blocked | Job → email/Slack | Any block (TEST-STRATEGY.md §5) |
| Data freshness | `/healthz` reports data end | Latest close older than 2 sessions → alert + site banner |
| AI spend | App counters + Anthropic limit | 50/80/100% of cap |
| Supabase usage | Supabase dashboard | DB > 70% of plan size; MAU > 70% |
| `/simulate` latency | Host metrics | p95 > 3 s for 30 minutes |

Alerts go to email in v1. Alerts that fire repeatedly without anyone acting on them get tuned or removed.

## 6. Backups and recovery

- **Supabase Pro daily backups, 7-day retention.** Free has no automatic backups, so Pro is required before real users arrive.
- **Weekly logical dump of the `market` schema** to private storage, kept for 8 weeks. It holds the versioned price history, which may not be re-fetchable later, depending on licence terms.
- User data is **not** dumped separately. Keeping it out of extra copies keeps deletion promises simple (SECURITY-PRIVACY.md §7).
- A restore drill into a scratch project before launch, then quarterly. Target RPO 24 h, RTO 4 h.
- Code, configuration and migrations live in git, and migrations are applied by CI.

## 7. Incidents

**Data-provider outage**
1. The nightly job fails or blocks, so no new dataset version is published. The site keeps serving the last published version, and every result shows "Data as of [date]".
2. The job retries hourly for 6 hours (`workflow_dispatch` from a retry workflow).
3. After 2 missed sessions: alert, plus a banner saying "Latest prices are delayed. Results use data up to [date]."
4. After 5 missed sessions: contact the provider. A secondary-provider adapter is possible (DATA-SOURCES.md §5) but needs its own licence. It is not planned for v1.
5. The simulation is unaffected apart from freshness. That is a property of the design: results are always pinned to a published dataset version.

**Wrong price or event discovered** (by a check, the adjusted-close cross-check, or a user report)
1. Mark the fund as "under review" so the UI shows a notice on results that use it.
2. Verify against an independent source: issuer distribution history, the fund's reports, or a second provider's data where the licence allows.
3. Publish a corrected **new dataset version**. Old rows are closed, never edited in place (PLAN.md §5).
4. Saved scenarios keep their stored results, pinned to the old version (R-12.4). On reopening they show "Corrected market data is available; re-run to update", plus a link to a changelog entry describing the correction.
5. Add a regression check or golden case for that error class.

**Engine bug**
- Every run stores `engine_version`, so affected runs can be found.
- Fix, add a golden case, release, then show the same "re-run to update" notice on affected runs.
