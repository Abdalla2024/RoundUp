# RoundUp — Security and Privacy

**Not legal advice.** This document is an engineering plan written without legal review. Everything in §8–§10 must be reviewed by a qualified lawyer before any public launch. That covers the privacy policy, the disclaimer wording, consumer-protection and financial-promotion questions, and data-protection obligations in each country where users may be located.

## 1. Principles

1. Collect as little as possible. A simulation needs dates and amounts, not who the user paid.
2. Uploaded transactions are processed in memory and discarded unless the user explicitly chooses to save them.
3. The API server cannot read or write other users' data, even if it has a bug (PLAN.md §4).
4. Deletion is real, immediate and complete.

## 2. What is stored and what is not

| Data | Stored? | Where | Notes |
|---|---|---|---|
| Email, auth identifiers, sessions | Yes | Supabase Auth (managed) | We never see or store passwords |
| Scenario configuration (funds, strategy, dates, seed, import counts) | Yes, if saved | `app.scenarios` | |
| Simulation results | Yes, if saved | `app.scenario_runs` | Derived numbers only |
| Uploaded CSV file | **No** | — | Parsed in API memory; the request body is not logged; temp files are not written |
| Transactions (date, amount cents, direction, category) | **Only if** the user ticks "Also save my transactions" | `app.scenario_transactions` | Off by default |
| Merchant descriptions | **No** by default (OPEN whether to offer it) | — | Used in memory for duplicate detection and classification, then dropped |
| Account numbers, card numbers, balances | **No** | — | The importer drops unknown columns; values that look like a full account or card number cause a warning and are never echoed back |
| Explainer prompts and outputs | Metadata only (tokens, question id, validator result) for 30 days | Logs | The prompt contains engine numbers only, no transactions |
| IP addresses | Short-lived, in host and rate-limit logs | Hosting providers | Retention set to the minimum each host allows (OPEN: verify per host) |
| Analytics | None in v1 beyond aggregate host metrics | — | No third-party trackers, no ads |

## 3. Authentication

- **Managed auth only: Supabase Auth.** Email magic link and/or OAuth (Google) is OPEN. We do not implement password storage, reset flows or session crypto ourselves.
- The browser sends the Supabase access token to FastAPI. FastAPI verifies the signature against Supabase's published keys, plus expiry and audience, and uses only the `sub` claim as the user id.
- Supabase docs: deleting a user does not sign them out. Their existing JWT stays valid until it expires (paraphrased from [managing user data](https://supabase.com/docs/guides/auth/managing-user-data)). We keep access-token lifetimes short, and the API refuses tokens for users that no longer exist.

## 4. Authorization and row-level security

- RLS is enabled on **every** table in exposed schemas. Supabase: "Enable RLS on every table in an exposed schema" ([RLS docs](https://supabase.com/docs/guides/database/postgres/row-level-security)).
- `app.*` policies: `select/insert/update/delete` only where `(select auth.uid()) = user_id`. Inserts check `user_id` too (`with check`).
- `market.*`: read-only for `anon` and `authenticated`. Writes only by the ingestion role used by the nightly job.
- `app.explainer_usage`: no direct client access. It is updated only through a narrow `security definer` function the API calls.
- FastAPI's database credentials are a read-only `market` role. It **does not** use the service-role key for normal requests.
- Tests: TEST-STRATEGY.md §7 (cross-user reads and writes return nothing or fail for every table).

## 5. Secrets

| Secret | Lives in | Never in |
|---|---|---|
| Supabase publishable (anon) key | Frontend env (public by design: "Safe to expose online", [API keys](https://supabase.com/docs/guides/api/api-keys)) | — |
| Supabase secret/service-role key | API host env var, used **only** by `DELETE /account` | Frontend, repo, logs. Supabase: "Never put one in a browser, a shipped application, or source control." |
| Market-data API key | GitHub Actions encrypted secret (nightly job) | API host, frontend |
| Ingestion DB role password | GitHub Actions secret | API host |
| Read-only market DB role | API host env | Frontend |
| Anthropic API key | API host env; key in a dedicated workspace with a spend limit | Frontend, job |
| HMAC key for result signatures | API host env; rotated with a key id | Anywhere else |

Controls:
- Secret scanning in CI (e.g. gitleaks) and GitHub push protection.
- A CI step greps the built frontend bundle for the service-role and secret key prefixes.
- `.env*` is git-ignored.
- Keys are rotated on any suspected exposure and at least yearly.

## 6. Other application security

- **Upload:** CSV only, ≤ 2 MB, ≤ 20,000 rows, strict parser, no formulas evaluated. Request bodies are excluded from logs. On export, cells starting with `=`, `+`, `-` or `@` are prefixed to prevent CSV injection.
- **Rate limits** per IP and per user on `/simulate`, `/parse` and `/explain`.
- **Explainer:** it receives only signed engine output, never transactions or descriptions, which closes the prompt-injection path through merchant names. Output is validated before display (TEST-STRATEGY.md §6).
- **Headers:** strict CSP (no third-party scripts), HSTS, `frame-ancestors 'none'`. CORS on the API allows only the site's origin.
- **Dependencies:** pinned lockfiles; Dependabot or Renovate; `pip-audit` and `npm audit` in CI.

## 7. Account and data deletion

- **Delete a scenario:** removes the scenario, its runs and any saved transactions (`on delete cascade`).
- **Delete account:** confirmed in the UI. Then `DELETE /account`:
  1. delete `app.*` rows for the user;
  2. call `auth.admin.deleteUser(uid)` (server-only; "Requires a `service_role` key", [docs](https://supabase.com/docs/reference/javascript/auth-admin-deleteuser));
  3. confirm by email.
- Supabase notes that you "cannot delete a user if they are the owner of any objects in Supabase Storage". We use no Storage in v1.
- **Backups:** deleted data persists in the provider's backups until they age out. On Supabase Pro, "Daily backups stored for 7 days" ([backups](https://supabase.com/docs/guides/platform/backups)). The privacy policy states this window.
- **Export:** "Download my data" (JSON of scenarios and runs). Recommended in v1 (cheap, and it supports data-access rights).

## 8. Privacy policy outline (for legal review)

1. Who we are and how to contact us.
2. What we collect: account email; saved scenarios and results; optionally saved transactions (dates, amounts, categories); technical logs.
3. What we do **not** collect: uploaded files (processed in memory and discarded), merchant names by default, bank or card credentials, account numbers.
4. Why we use it: to provide the simulation and saved scenarios; security; nothing else. No advertising, no sale of data, no profiling.
5. AI explainer: which numbers are sent to the AI provider (results only, no transactions); the provider's data-retention terms (OPEN: cite Anthropic's commercial terms after review).
6. Processors: Supabase (auth, database), Vercel (site), the API host, the market-data provider (receives no user data), Anthropic (receives result numbers), error monitoring (receives no request bodies). Hosting regions.
7. Retention: account data until deletion; logs N days; backups up to 7 days after deletion.
8. Your rights: access/export, correction, deletion; how to exercise them; the right to complain to a regulator (jurisdiction-specific).
9. Children: not intended for under-13s (or the higher local age). Age gate OPEN.
10. Changes to the policy; effective date.

## 9. Disclaimer wording (draft, for legal review)

**Short (on every results screen, above the numbers):**

> **Hypothetical historical simulation.** These results show what *might* have happened if round-ups had been invested in the past, using historical market prices. No money was invested. Past performance does not predict future results. This is not investment, tax or financial advice.

**Long (assumptions panel and footer link):**

> RoundUp is an educational tool. It calculates what spare-change round-ups from your sample or uploaded transactions would have been worth if they had been invested in the selected fund on the dates and at the prices described in "How this works". No money moves, no trades are placed, and you cannot invest through RoundUp.
>
> The results are hypothetical and backward-looking. They rely on simplifying assumptions: purchases at the next trading day's closing price, fractional shares, no commissions or trading costs, no taxes, no app or account fees, and dividends handled as described. Real accounts would differ. The funds shown were chosen because they are well known today, and that choice itself benefits from hindsight. Historical returns do not predict future returns, and you could lose money investing.
>
> Nothing on RoundUp, including the AI explanations, is a recommendation to buy, sell or hold any security, or to use any product. Consider speaking with a qualified, independent professional before making financial decisions.
>
> Market data provided by [provider], used under licence. Data may contain errors; see "Data as of [date]".

## 10. Launch blockers (must be reviewed or closed before public launch)

1. Legal review of: the disclaimer, privacy policy, terms of use, and whether showing named real funds with hypothetical returns raises any advertising, financial-promotion or investment-adviser concerns in our target jurisdictions.
2. A market-data **display licence** signed (DATA-SOURCES.md §6), with attribution implemented as the licence requires.
3. Applicable data-protection regimes for our target users (e.g. GDPR/UK GDPR, US state laws). Determines DPAs, records of processing, hosting region and cookie notice. There are no non-essential cookies in v1.
4. Data processing agreements with Supabase, Vercel, the API host and Anthropic, plus each vendor's retention terms.
5. Age policy.
6. Whether Vercel Hobby and Supabase Free terms allow our use (non-commercial question).
7. A penetration-style review of RLS policies and the API before launch.
