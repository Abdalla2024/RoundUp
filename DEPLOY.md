# Deploying RoundUp (owner steps)

Two Vercel Hobby projects from one repository, plus the Supabase project you created. This file was rewritten on 2026-10-13 after the first **preview** deployment. Nothing here contains a secret. The only values quoted are public ones (the project URL and the publishable key).

**Legend.** ✅ checked on the real service on 2026-10-13 (the evidence is named). ⚠️ not checked yet. ✋ only you can do it.

## 0. What exists now (preview demo)

| Item | Value | State |
|---|---|---|
| API project | Vercel project `roundup-api`, Root Directory = repository root, preset FastAPI | ✅ |
| Web project | Vercel project `roundup-web`, Root Directory = `web`, preset Next.js | ✅ |
| API address | `https://roundup-demo-api-pr.vercel.app` (alias of a preview deployment) | ✅ |
| Web address | `https://roundup-demo-web-pr.vercel.app` (alias of a preview deployment) | ✅ |
| Supabase | project ref `rauwjvyaluuxivnktxtk` | ✅ |
| Git link | **none** (deployed from a local copy with the CLI; pushes do not deploy) | ✅ |
| Production deployment | **none intended.** One accidental one exists, see §2 | ⚠️ |

## 1. API project

**Dashboard route** (Vercel → Add New → Project → import the repository): Root Directory = the repository root (`./`), not `api/`. Vercel: with a Root Directory set, "Your app will not be able to access files outside of that directory" ([docs](https://vercel.com/docs/builds/configure-a-build#root-directory)); the API needs `engine/`.

**CLI route actually used** (no Git link; each command was shown first and approved):
1. Create the project through the REST API with a JSON file that sets `name`, `framework: "fastapi"`, `rootDirectory: null`, `ssoProtection: null` and the preview environment variables: `npx vercel@63.1.2 api /v11/projects -X POST --input api.json` ([create-project reference](https://vercel.com/docs/rest-api/projects/create-a-new-project)). ✅
2. Link this folder to the project: `npx vercel@63.1.2 link --yes --project roundup-api` (writes `.vercel/` and `.env.local`, both ignored by git). ✅
3. Deploy a preview from the repository root: `npx vercel@63.1.2 deploy --yes`. ✅
4. Give it the fixed address: `npx vercel@63.1.2 alias set <deployment-url> roundup-demo-api-pr.vercel.app`. ✅ The alias answered `DEPLOYMENT_NOT_FOUND` for about 20 seconds, then worked.

**What the real build taught us**
- ✅ Vercel installs with **uv** (install command `pip install -r requirements.txt`; build log). A bare `./engine` line in `requirements.txt` **failed**: "Package metadata name `roundup-engine` does not match given name `engine`". The file now says `roundup-engine @ ./engine` and `roundup-api @ ./api`, which Vercel accepts. **It does not work with pip** ("Invalid URL './engine': No scheme supplied"; this broke GitHub CI on 2026-10-14, and this line of DEPLOY.md was wrong). pip, CI and local setup therefore use `requirements-ci.txt`, derived from `requirements.txt` by `python tools/check_requirements.py --write`; CI runs `python tools/check_requirements.py` first, which installs both files in fresh environments.
- ✅ Vercel used **Python 3.12.14**, because no version file exists. Everything was developed on 3.13.2, so the suites were rerun on Python 3.12.15: engine 446, API 100 and independent API 514 pass, and the 208-scenario cross-check shows 0 differences.
- ✅ `.vercelignore` (repository root) keeps tests, fixtures, mocks, screenshots, `crosscheck/`, `supabase/` and `.venv` out of the upload: 84 files, about 490 KB. The function's own `excludeFiles` in `vercel.json` is a second guard.
- ✅ `https://roundup-demo-api-pr.vercel.app/v1/health` returns `{"status":"ok",…}`.

## 2. Web project

**CLI route used:** create with a JSON file (`framework: "nextjs"`, `rootDirectory: "web"`, `ssoProtection: null`, three `NEXT_PUBLIC_*` variables for the preview target) ✅; `vercel link --yes --project roundup-web` ✅; `vercel deploy --yes` from the **repository root** (the project's Root Directory `web` is applied by Vercel) ✅; then `vercel alias set … roundup-demo-web-pr.vercel.app` ✅. A folder can be linked to only one project at a time, so relink before deploying the other project.

**Gotchas found**
1. ✅ **A project's first deployment becomes a production deployment, even without `--prod`.** The web project's first deploy was marked `target production` and went live at `roundup-web.vercel.app`. Because its variables were set for *Preview only*, that build had no API address and pointed at `127.0.0.1:8000`. A second deploy was a normal preview. **That accidental production deployment is still live and should be removed** (§9, step 1c). To avoid this: set every variable for both Production and Preview, or make the first deployment on purpose.
2. ✅ `NEXT_PUBLIC_*` values are baked into the JavaScript at build time. Change one, then redeploy.
3. ✅ New projects have Vercel Authentication on for previews, which would block both the browser and outside tests. It was turned off (`ssoProtection: null`) for the one-week demo, on your approval ([docs](https://vercel.com/docs/deployment-protection/methods-to-protect-deployments/vercel-authentication)). The preview addresses are therefore public, though unlisted.
4. ✅ On previews, Vercel injects its own feedback-toolbar script from `vercel.live`. Our Content-Security-Policy blocks it, which logs one console error on previews only. This is expected.
5. ⚠️ `roundup.vercel.app` could not be confirmed as free (it answered differently from unused names), so the `-pr` names are used.

## 3. Environment variables

| Name | Project | Where the value comes from | Set for | State |
|---|---|---|---|---|
| `SUPABASE_URL` | API | Supabase → Project Settings → API: project URL (also the token issuer, `<URL>/auth/v1`) | Preview | ✅ |
| `SUPABASE_PUBLISHABLE_KEY` | API | Supabase → API Keys: **publishable** key. Never the secret / service-role key | Preview | ✅ |
| `ALLOWED_ORIGIN` | API | The web address, no trailing slash: `https://roundup-demo-web-pr.vercel.app` | Preview | ✅ |
| `ROUNDUP_TRUST_PROXY` | API | The literal `1`. Vercel overwrites `X-Forwarded-For` "to prevent IP spoofing" ([docs](https://vercel.com/docs/headers/request-headers)) | Preview | ✅ (rate limit confirmed, §5) |
| `LOG_SALT` | API | Optional. Left **unset** for the demo: each server instance picks a random salt, so hashed client ids in the logs differ between instances | — | ✅ |
| `NEXT_PUBLIC_API_URL` | web | `https://roundup-demo-api-pr.vercel.app` | Preview | ✅ |
| `NEXT_PUBLIC_SUPABASE_URL` | web | Same as `SUPABASE_URL` | Preview | ✅ |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | web | Same publishable key (public by design) | Preview | ✅ |
| `NEXT_PUBLIC_AUTH_MODE` | — | **Never set on Vercel.** It switches on the local test stand-in; the build refuses it, and a build without it contains no stand-in code (checked: no `standin` text in `.next/static`, and none in the deployed bundle) | — | ✅ |

For a later production deployment, add every variable above for **Production** too (and set `ALLOWED_ORIGIN` to the production web address).

### 3.1 CORS ✅
Checked from outside with `curl` against the deployed API:
- preflight from `https://roundup-demo-web-pr.vercel.app` → `200`, `access-control-allow-origin` = that address, methods `GET, POST`, headers `Accept, Accept-Language, Authorization, Content-Language, Content-Type`;
- preflight from `https://example.com`, `null`, `https://roundup-web.vercel.app` and `https://roundup-demo-web-pr.vercel.app.evil.com` → `400`, no allow-origin header;
- a real POST from another origin gets no allow-origin header.

Preview deployments at other addresses cannot call this API. That is expected.

### 3.2 Supabase URLs for sign-in
Authentication → URL Configuration: Site URL = `https://roundup-demo-web-pr.vercel.app`; Redirect URLs = `https://roundup-demo-web-pr.vercel.app/auth/callback`. ✋ You set both. ⚠️ I could not read them back: they are not public, and the CLI route needs `supabase init` plus `config pull` (not run). `supabase link --project-ref …` itself worked and did not ask for the database password ✅.
Checked from outside: ✅ sign-ups are disabled (`disable_signup: true`), email sign-in is on, anonymous sign-ins are off, and a magic-link request for an unknown address answers "Signups not allowed for otp" with no user created.

## 4. Smoke test

**Automated, from outside, no credentials** (`web/e2e-deployed`; inside `web/` run `DEPLOY_WEB=… DEPLOY_API=… npx playwright test -c playwright.deployed.config.ts`): ✅ 6 tests pass: simulate, compare, CSV upload, saved page signed out, the bundle check, accessibility in light/dark/mobile on 6 screens (18 runs, 0 violations), and page weight. It never signs in, so it sends no email.

**By hand (✋ needs a real invited address; sends one email):**
1. Authentication → Users → invite one address. (Open sign-ups stay off.)
2. On the results page choose **Sign in to save**, enter that address, open the email link. It opens a new tab.
3. ⚠️ Check whether the original tab now shows **Save this scenario** (OQ-11). If not, reload Saved scenarios in the new tab. (Steps 1–4 were done by the owner on 2026-10-13 and worked.)
4. Save, see it listed, open it, delete it.
5. Two-user check: user B must not see A's scenario (supabase/README.md §4).
6. Vercel → API project → Logs: one JSON line per request, no emails, amounts or merchant names.

## 5. Pre-launch checklist

| Check | How | State |
|---|---|---|
| Disclaimers visible | Label strip, yellow box and Key points on results and compare; footer everywhere. Exact text: COPY.md | ✅ (deployed test) |
| Privacy page | `/privacy` loads and matches what you tell invitees | ✅ loads; ✋ read it |
| Sign-ups off | Supabase → Authentication | ✅ (public settings endpoint) |
| Tables closed to signed-out visitors | Requests with the publishable key only are refused (401, permission denied) on all three tables for read, insert and delete, and on both RPC functions | ✅ |
| Row-level security, two users | `supabase/tests/rls_negative_test_selfcontained.sql` in the SQL editor: `ALL RLS CHECKS PASSED` | ✅ (you ran it; it leaves no users by design) |
| Forged tokens refused | Six forged tokens (none, garbage, HS256, `alg=none`, own ES256 key with a real key id, unknown key id) → all 401 | ✅ |
| A real token accepted | The owner signed in with a real magic link, saved a scenario through the API and saw it in Saved scenarios | ✅ owner, 2026-10-13 |
| Rate limits on | 24 quick POSTs answered, then `429` | ✅ (per server instance only) |
| Cost cap | Hobby has no paid usage; Supabase Free has fixed quotas; no AI key. If you ever move to Pro, set Spend Management ([docs](https://vercel.com/docs/projects/managing-projects)) | ✅ |
| No secrets in the repo | `git grep -nE "sb_secret_\|-----BEGIN [A-Z ]*PRIVATE KEY\|eyJhbGciOi[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}" -- ':!DEPLOY.md'` returns nothing | run before each launch |
| CI | GitHub → Actions: the Python jobs passed; the web job failed on a real bug (a rate-limit race), now fixed locally | ⚠️ rerun after you push |
| Backups | None on Supabase Free. Saved scenarios are not backed up (the Saved page says so) | ✅ |

## 6. Security headers and errors (checked on the deployed previews)

- API ✅: `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` on POST responses and errors, `Strict-Transport-Security` (from Vercel). The first four were added in this stage; before it, none were set.
- Web ✅: a Content-Security-Policy that allows only this site, the API and Supabase for connections, no framing, no plugins, no remote scripts; plus `nosniff`, `X-Frame-Options: DENY`, a referrer policy and a permissions policy. Scripts and styles still allow `'unsafe-inline'`, because Next.js and React use inline scripts and styles. That is a known limit.
- Errors ✅: a hostile field *name* used to come back in `error.fields`. Non-plain names now appear as `?`. Script text in values, bad JSON, wrong content types, bad tokens, odd paths and a 4 MB body all return fixed plain messages that never include the input.
- ✅ `access-control-allow-origin: *` appears on the web app's static pages (Vercel's default for static files). They hold no user data.

## 7. Real numbers on Vercel (preview, measured from this laptop, so timings include the network round trip)

| Measure | Local | Vercel preview |
|---|---|---|
| Setup page, first load | 614 KB, about 150–200 KB transferred | 860 KB, 226 KB transferred |
| Full-range simulation, `buys: none` | 59,313 bytes, about 150 ms | 59,313 bytes, 333–459 ms (5 runs) |
| Full-range comparison | 118,384 bytes, about 245 ms | 118,384 bytes, 627–743 ms (5 runs) |
| Run to the results page | 1,015 KB, about 175 KB transferred | 1,262 KB, 119 KB transferred |

The setup page is bigger on Vercel because the deployed build loads the Supabase browser library (243 KB uncompressed, verified by listing the scripts) on every page, while the local test build does not. Loading it only when someone signs in would remove that; this is not done yet.

## 8. Verified by the owner on 2026-10-13, and still not verified

**✅ Verified by the owner on 2026-10-13, on the preview with the real services:** invited their own address, signed in with a real magic link (so email delivery, the code exchange on `/auth/callback`, and `shouldCreateUser: false` with the invite flow work), ran a simulation, saved it (the API accepted the real token and called `save_scenario` with it), and saw it in Saved scenarios (the nested-results read under row-level security works). Also a short VoiceOver pass (a fuller one is planned).

**Still not verified:**

- Whether the tab that started the sign-in sees the session created in the magic-link tab (OQ-11): the owner's note does not say which tab was used.
- Deleting a saved scenario, and the two-user check on the real service (user B must not see A's scenario).
- Site URL and Redirect URLs read back from Supabase.
- GitHub Actions on the new commits.
- A Python 3.12 job in CI (the suites pass on 3.12 locally, but CI runs only 3.13.2).

If any of these fails, stop and send me the log or the message.

## 9. Taking everything down after the presentation (checklist)

Do these in order. Each has a check afterwards. ⚠️ **None of these commands has been run yet** (taking the demo down is irreversible, so they were not rehearsed); the command names come from the CLI reference ([Vercel](https://vercel.com/docs/cli/project), [alias](https://vercel.com/docs/cli/alias)). That pausing leaves preview addresses working is my reading of "pauses production traffic", not something I tested.

1. **Vercel (both projects)**
   a. Quick stop (reversible): `npx vercel@63.1.2 project pause roundup-web` and `… pause roundup-api`. You type each project name to confirm. This pauses *production* traffic only, so the preview addresses keep working: do (b) as well ([docs](https://vercel.com/docs/cli/project)).
   b. Remove the previews: `npx vercel@63.1.2 alias rm roundup-demo-web-pr.vercel.app` and `… roundup-demo-api-pr.vercel.app`, then delete the projects: `npx vercel@63.1.2 project rm roundup-web` and `… roundup-api`. Deleting a project deletes its deployments, domains and environment variables. The `.vercel.app` names become free for anyone to take.
   c. The accidental production deployment of `roundup-web` goes with the project in (b). If you keep the project, remove that one deployment first: `npx vercel@63.1.2 remove roundup-2r96zp4tq-abdalla-abdelmagids-projects.vercel.app`. **Always pass the full deployment URL.** Vercel's own docs warn that `vercel remove <project-name>` removes the entire project ([docs](https://vercel.com/docs/cli/remove)).
   d. Check: `curl -sI https://roundup-demo-web-pr.vercel.app/` and `…api-pr.vercel.app/v1/health` return `404` with `x-vercel-error: DEPLOYMENT_NOT_FOUND`; so does `https://roundup-web.vercel.app/`.
2. **Supabase**
   a. Authentication → Users: delete every user you invited (this also removes their saved scenarios, through the foreign keys). Check Table Editor → `scenarios` and `scenario_results` are empty.
   b. Project Settings → General → **Pause project**, or **Delete project** to remove all data for good. (`npx supabase@2.120.0 projects delete rauwjvyaluuxivnktxtk` also deletes it.)
   c. If the project stays: Authentication → URL Configuration, remove the web address from Site URL and Redirect URLs.
   d. Check: `curl -s https://rauwjvyaluuxivnktxtk.supabase.co/auth/v1/settings -H "apikey: <publishable key>"` no longer returns the settings.
3. **GitHub:** make the repository private or archive it. No Actions secrets were used, so there is nothing to delete there.
4. **Local machine:** delete the `.vercel/` folder and the `.env.local` file in the repository root, run `npx vercel@63.1.2 logout` and `npx supabase@2.120.0 logout`, and revoke the CLI tokens if you want: Vercel → Account Settings → Tokens; Supabase → Account → Access Tokens.
5. **Invitees:** tell them their saved scenarios are deleted. No payment details or merchant names were ever stored.
