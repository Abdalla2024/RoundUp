# Deploying RoundUp (owner steps)

Two Vercel Hobby projects from one Git repository, plus the Supabase project you create. No real values appear in this file. Every `<…>` is something you fill in from your own dashboards. Nothing here has been run against a live account yet; the first deploy is where the unverified points in §6 get confirmed.

**Before you start:**
- The repository needs to be on GitHub (or GitLab/Bitbucket) for Vercel to import it. This repo has not been pushed.
- Have the Supabase project set up per [supabase/README.md](supabase/README.md) steps 1–3: SQL applied, asymmetric signing key, sign-ups off, negative test passed.

## 1. API project (Root Directory = repository root)

1. Vercel dashboard → **Add New… → Project** → import the repository.
2. **Root Directory:** leave it as the repository root (`./`). Do **not** choose `api/`.
   - Vercel: with a Root Directory set, "Your app will not be able to access files outside of that directory. You also cannot use `..`" ([docs](https://vercel.com/docs/builds/configure-a-build#root-directory)).
   - The API needs `engine/`, so it deploys from the root, using `app.py`, `requirements.txt` and `vercel.json`.
3. **Framework preset:** FastAPI or Python. Vercel finds the `app` object in `app.py` ([docs](https://vercel.com/docs/frameworks/backend/fastapi)).
4. **Project name:** e.g. `roundup-api`. Vercel assigns "a domain based on your project name and ending in `.vercel.app`… allocated on a first-come, first-served basis" ([docs](https://vercel.com/docs/domains/working-with-domains)). Note the address it gives you: `https://<api-project>.vercel.app`.
5. Set **Environment Variables** (Settings → Environment Variables, environment **Production**) from the table in §3. For now, set `ALLOWED_ORIGIN` to a placeholder such as `https://example.invalid`; it gets its real value in step 3.1 once the web project exists.
6. Deploy. Check: `https://<api-project>.vercel.app/v1/health` should return `{"status":"ok",…}`.

## 2. Web project (Root Directory = `web`)

1. **Add New… → Project** → the same repository.
2. **Root Directory:** `web`. **Framework preset:** Next.js.
3. **Project name:** e.g. `roundup-web`. Its default address is `https://<web-project>.vercel.app`.
4. Set the web environment variables from §3. `NEXT_PUBLIC_*` values are built into the site at build time, so redeploy after changing any of them ([Next.js](https://nextjs.org/docs/app/guides/environment-variables)).
5. Deploy.

## 3. Environment variables

| Name | Project | Where the value comes from | Notes |
|---|---|---|---|
| `SUPABASE_URL` | API | Supabase → Project Settings → API: project URL | Also the token issuer: `<SUPABASE_URL>/auth/v1` |
| `SUPABASE_PUBLISHABLE_KEY` | API | Supabase → API Keys: **publishable** key | Never the secret/service-role key |
| `ALLOWED_ORIGIN` | API | The web project's default address, `https://<web-project>.vercel.app` (no trailing slash) | The only origin CORS allows (owner decision) |
| `ROUNDUP_TRUST_PROXY` | API | The literal value `1` | Rate limits use the client IP, which Vercel overwrites in `X-Forwarded-For` "to prevent IP spoofing" ([docs](https://vercel.com/docs/headers/request-headers)) |
| `LOG_SALT` | API | Any long random string you generate, e.g. `python3 -c "import secrets; print(secrets.token_hex(16))"` | Salts the hashed client id in logs; keep it out of the repo |
| `NEXT_PUBLIC_API_URL` | web | `https://<api-project>.vercel.app` | |
| `NEXT_PUBLIC_SUPABASE_URL` | web | Same as `SUPABASE_URL` | |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | web | Same publishable key | Safe in the browser by design |
| ~~`NEXT_PUBLIC_AUTH_MODE`~~ | — | **Never set this on Vercel.** It switches on the local test stand-in | The build refuses it on Vercel (`web/next.config.ts`) |

There is no Anthropic or other AI key in this stage: the explainer is a placeholder.

### 3.1 Restrict CORS to the web address

1. Copy the web project's default address from its dashboard (Domains), e.g. `https://roundup-web.vercel.app`.
2. In the **API** project, set `ALLOWED_ORIGIN` to exactly that value: scheme included, no trailing slash, no wildcard.
3. **Redeploy the API.** Environment changes apply to new deployments.
4. Check from your own terminal, with your real addresses in place of the placeholders:
   ```bash
   curl -s -o /dev/null -D - -X OPTIONS https://<api-project>.vercel.app/v1/simulate \
     -H "Origin: https://<web-project>.vercel.app" -H "Access-Control-Request-Method: POST" | grep -i access-control-allow-origin
   ```
   It should print your web address.
5. Repeat with `-H "Origin: https://example.com"`. It should print nothing.
6. Preview deployments use other addresses, so they cannot call the production API. That is expected.

### 3.2 Supabase URLs for sign-in

- Supabase → Authentication → URL Configuration:
  - **Site URL** = `https://<web-project>.vercel.app`
  - **Redirect URLs** = `https://<web-project>.vercel.app/auth/callback`
- Invite your cohort from Authentication → Users (open sign-ups stay **off**). The app asks Supabase not to create users on sign-in (`shouldCreateUser: false`).

## 4. After the first deploy: smoke test (about 10 minutes)

1. Open the web address signed out. Run the default sample simulation, then compare.
2. Upload a small CSV (date, amount, description). Choose "Purchases are positive numbers" and check the file. Run it.
3. On the results page choose **Sign in to save** and enter an invited email. Check the magic-link email arrives; the link opens a new tab on Saved scenarios.
4. Go back to the first tab. If **Save this scenario** has appeared, the session reached it (OPEN-QUESTIONS OQ-11); if not, reload Saved scenarios in the new tab and save from a fresh run there. Save a scenario. It should appear in the list; open it, then delete it.
5. Two-user check: as user B in a private window, A's scenario must not appear (supabase/README.md §4).
6. Look at Vercel → API project → Logs. There should be one JSON line per request, with no emails, amounts or merchant names.

## 5. Pre-launch checklist

| Check | How |
|---|---|
| **Disclaimers visible** | On the results and compare screens: the label strip "Synthetic scenario. Not a real fund, not real prices, and not a forecast.", the yellow "Hypothetical simulation on a synthetic market…" box, and the Key points. The footer on every page. Exact text: COPY.md |
| **Privacy page** | `/privacy` loads and matches what you're comfortable telling invitees. It's linked in the footer |
| **Sign-ups off** | Supabase → Authentication: new sign-ups disabled; only invited emails can sign in |
| **Test users removed** | Delete the two RLS test users after supabase/README.md §3 |
| **Rate limits on** | `ROUNDUP_TRUST_PROXY=1` set. Limits are per server instance (API.md), enough to slow abuse in an invite-only demo |
| **Cost cap** | Hobby has no paid usage to cap. Supabase Free has fixed quotas. There is no AI key in this stage. If you later move to Vercel Pro, set Settings → Spend Management → "Pause all production deployments" ([docs](https://vercel.com/docs/projects/managing-projects)) |
| **No secrets in the repo** | `git grep -nE "sb_secret_\|-----BEGIN [A-Z ]*PRIVATE KEY\|eyJhbGciOi[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}" -- ':!DEPLOY.md'` returns nothing (secret keys, private keys, or long signed tokens) |
| **CI green** | GitHub → Actions: the `ci` workflow passes on the commit you deploy |
| **Backups** | None on Supabase Free (OPERATIONS.md). Invitees are told saved scenarios are not backed up (Saved page intro) |

## 6. Not yet verified (confirm on the first deploy)

- Vercel's Python installer accepting the local-path lines `./engine` and `./api` in `requirements.txt`.
- Vercel detecting the root `app.py` while `web/` holds a separate Next.js project in the same repository.
- The Supabase magic-link round trip and PKCE code exchange on `/auth/callback`. Tested only against the local stand-in; supabase-js handles it with `detectSessionInUrl`.
- Whether a tab that started the sign-in sees the session created in the magic-link tab (OQ-11).
- `shouldCreateUser: false` blocking uninvited emails, together with the dashboard sign-up switch.
- Supabase listing saved scenarios with nested results (`select=…,scenario_results(…)`) under RLS. The local stand-in implements the same shape.

If any of these fails, stop and send me the build log or the error message.

## 7. Taking the site down after the presentation

1. **Pause both Vercel projects:** Project → Settings → General → **Pause Project** → type the project name → **Pause Project**. Visitors then see a "503 DEPLOYMENT_PAUSED" page. **Resume Project** brings it back within minutes without redeploying ([docs](https://vercel.com/docs/projects/managing-projects)).
2. **To remove it for good:** Settings → General → **Delete Project**, which deletes deployments, domains and environment variables. Note that the `.vercel.app` name is then free for others to claim.
3. **Supabase:** pause the project from its dashboard, or delete it to remove all saved data. Free projects also pause by themselves after a week without requests.
4. **Repository:** make it private, or archive it, if it was public.
