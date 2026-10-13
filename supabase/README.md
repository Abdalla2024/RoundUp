# Supabase setup for RoundUp

You create the project; these files set up the database. Nothing here contains secrets.

| File | What it does |
|---|---|
| `migrations/0001_schema.sql` | Tables `scenarios`, `scenario_results`, `explainer_usage` (in `public`), indexes, `updated_at` trigger |
| `migrations/0002_rls.sql` | Row-level security, least-privilege grants, `save_scenario()` (atomic save), `record_explainer_usage()` |
| `tests/rls_negative_test.sql` | Two-user negative test you run in the SQL editor (rolled back, leaves nothing behind) |
| `tests/local_supabase_shim.sql`, `tests/test_rls_local.py` | How I tested the same SQL on a local Postgres. Not for Supabase |

## 1. Apply the SQL (once)

1. Supabase dashboard → your project → **SQL Editor** → **New query**.
2. Paste all of `migrations/0001_schema.sql` → **Run**. Expect "Success. No rows returned".
3. New query: paste all of `migrations/0002_rls.sql` → **Run**. Expect the same.

If either step errors, stop and send me the message. Don't edit the SQL by hand.

## 2. Settings to check (dashboard)

| Where | Setting | Why |
|---|---|---|
| Table Editor | Each of the 3 tables shows **RLS enabled** | Supabase: "Enable RLS on every table in an exposed schema" |
| Authentication → Sign In / Providers | **Email** on, using magic links. Turn **off** "Allow new users to sign up" and invite your cohort instead | Invite-only demo (D-9) |
| Authentication → URL Configuration | Site URL = your default Vercel address (e.g. `https://<project>.vercel.app`); add the same address to Redirect URLs | Magic-link emails must return to the site |
| Project Settings → JWT / Signing Keys | Use an **asymmetric** signing key (ES256 or RS256) as the current key | The API verifies tokens with the project's JWKS. Supabase: the JWKS endpoint "does not return any keys if you are not using asymmetric JWT signing keys" |
| Project Settings → API Keys | Copy the **project URL** and the **publishable** key (safe in the browser) | Set later as Vercel env vars `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`. **Never** put the secret / service-role key in the web app |

## 3. Negative test as two test users (SQL editor)

1. Authentication → Users → **Add user** twice (e.g. `test-a@…`, `test-b@…`). Copy each user's **UID**.
2. Open `tests/rls_negative_test.sql`, replace the two placeholder UUIDs near the top with user A's and user B's UIDs, paste the whole file into a new query → **Run**.
3. **Expected:** the result grid shows one row, `ALL RLS CHECKS PASSED`. Under "Messages" or "Notices" there should be 14 lines beginning `PASS:`.
4. **If anything leaks**, the run stops with an error starting `FAIL:` that says what leaked. Send it to me.
5. The script ends with `rollback`, so it creates no lasting rows. You can delete the two test users afterwards.

What it checks:
- User B cannot read, rename or delete user A's scenarios or results.
- User B cannot create rows owned by A, or attach a result to A's scenario (that one is blocked by a constraint, because foreign-key checks bypass RLS).
- Results cannot be edited by anyone; only a scenario's name can change.
- Usage counters are written only through the function, and each user sees only their own.
- A signed-out visitor (`anon`) cannot read anything or call the save function.
- User A's data is intact at the end.

## 4. Negative test through the real API layer (after the site is deployed, Part 2)

Same idea, using two real sign-ins:
1. Sign in as A, save a scenario, and note its id. Sign in as B in a private window.
2. As B, the saved list must not show A's scenario.
3. Requesting `GET <SUPABASE_URL>/rest/v1/scenarios?id=eq.<A's id>` with B's access token and the publishable key returns `[]`.
4. `POST <SUPABASE_URL>/rest/v1/scenarios` with B's token and body `{"user_id": "<A's id>", "name": "x", "config": {}}` is refused (HTTP 403, "new row violates row-level security policy").

I'll provide a small script for this in Part 2.

## What I verified locally, and what I could not

- **Verified:** I ran the same SQL on a local Postgres (Postgres.app) with a shim that mimics Supabase's `auth` schema, roles and default grants. `auth.uid()` was copied from Supabase Auth's source. Results:
  - The negative script passes.
  - It **fails, as it should**, when any of five leaks is planted: a permissive select policy, an updatable results table, an anon policy, RLS disabled, or the ownership constraint removed.
  - Account deletion cascades to every row.
  - `save_scenario` is all-or-nothing.
- **Not verified, because it needs your project:**
  - The real Supabase roles, default grants and Data API behaviour.
  - Whether the dashboard's SQL editor shows `NOTICE` lines.
  - Whether your project's signing key is asymmetric.
  - The magic-link flow.
- **API follow-up (Part 2):** the API currently saves with two inserts. It will switch to one call to `POST /rest/v1/rpc/save_scenario`, which closes API.md question #34 (partial saves).
