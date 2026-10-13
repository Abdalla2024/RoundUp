# RoundUp frontend: proposed structure (stage 4, Part 2)

**Status:** built in stage 5 (`web/`). The exact wording comes from COPY.md. Where the build differs from the proposal below, the "As built" notes win.

**As built (stage 5):**
- **Sign-in is browser-only, with `@supabase/supabase-js`** (PKCE magic link), not `@supabase/ssr`. The ssr README: "If you don't need server-side access to the session, use `@supabase/supabase-js`'s `createClient` directly… there's no reason to use `@supabase/ssr` in that case" ([README](https://github.com/supabase/ssr)). The API verifies every token itself, and saved scenarios are read under RLS, so the site has no server-side trust decisions.
- **A test stand-in for sign-in** (`tools/standin/`, `NEXT_PUBLIC_AUTH_MODE=standin`) lets the end-to-end tests sign in and save with no real credentials. `web/next.config.ts` refuses to build it on Vercel.
- **Lazy loading:** the Supabase client loads on first sign-in use, and Recharts loads when a chart is shown (`components/ChartCanvas.tsx`). That cut the setup page's first load from 1,090 KB to 606 KB uncompressed (200 KB transferred).
- **Key points always visible:** on mobile they sit at the top of the page, with the full list collapsed, instead of in a dialog.
- **The only number-from-string conversion** is in the chart's drawing files (`ValueChart.tsx` for the axis top, `ChartCanvas.tsx` for line positions). A test enforces this (`web/tests/no-money-arithmetic.test.ts`).

## 1. Stack

| Choice | Why | Source |
|---|---|---|
| **Next.js (App Router) + TypeScript**, a separate Vercel project rooted at `web/` | Owner decision. Static-friendly pages, with server rendering only where it helps. | — |
| **Supabase Auth via `@supabase/ssr` + `@supabase/supabase-js`** | Supabase: "The `@supabase/ssr` package handles this for JavaScript and TypeScript applications" (cookie-based sessions for Next.js). | [Supabase Next.js auth](https://supabase.com/docs/guides/auth/server-side/nextjs) |
| **Recharts 3** for charts (§4) | Keyboard navigation built in and on by default; React-native SVG. | [Recharts accessibility wiki](https://github.com/recharts/recharts/wiki/Recharts-and-accessibility) |
| Plain CSS with the design tokens from `web/mocks/styles.css` (CSS custom properties, light and dark) | The tokens are already contrast-checked. No CSS framework needed for four screens. | — |
| Inter via `next/font/google` | DESIGN.md type choice; self-hosted at build time. | — |

## 2. Folder structure

```
web/
  app/
    layout.tsx                 header, label strip, footer, skip link, theme tokens
    page.tsx                   landing → "Generate sample spending" (signed-out friendly)
    simulate/page.tsx          scenario setup (client component: form state)
    results/page.tsx           results for the last run (held in memory in a React context; not stored)
    compare/page.tsx           side-by-side comparison
    saved/page.tsx             saved scenarios (signed in) / sign-in prompt (signed out)
    auth/callback/route.ts     magic-link return (exchange code for session)
  components/
    ValueChart.tsx             Recharts wrapper: value line + "added" line, rule caption, summary, table toggle
    StatTiles.tsx  Headline.tsx  AssumptionsPanel.tsx  Disclaimer.tsx  ScenarioCard.tsx  ErrorState.tsx
  lib/
    api.ts                     typed client for API.md (fetch, error envelope → ApiError)
    format.ts                  formatting ONLY: "1789.92" → "$1,789.92", dates, counts. No arithmetic on money.
    supabase/{client,server}.ts
  tests/  (unit)   e2e/  (Playwright)
```

**Rule carried over from the API:** the frontend never calculates a figure people see. Every number is an API string. `format.ts` only adds `$`, separators and signs. A lint test bans `parseFloat`/`Number(` on result fields outside the chart component, where they are used only for pixel positions.

## 3. How the site calls the API

- The browser calls the API directly at `NEXT_PUBLIC_API_URL`.
  - Next.js: values are inlined at build time, and "Non-`NEXT_PUBLIC_` environment variables are only available in the Node.js environment" ([Next.js env vars](https://nextjs.org/docs/app/guides/environment-variables)).
  - The only public values are the API URL, the Supabase URL and the Supabase **publishable** key.
- **CORS (owner decision):** the API allows exactly one origin, the web project's default Vercel address `https://<web-project>.vercel.app`, set as an API env var (`ALLOWED_ORIGIN`).
  - Allowed methods: `GET, POST`. Allowed headers: `Content-Type`, `Authorization`. No credentials mode; the token goes in a header, not a cookie.
  - **Consequence:** Vercel *preview* deployments (other URLs) cannot call the production API. Previews can point at a preview API, or be tested locally.
- Endpoints used:
  - `GET /v1/scenarios` and `GET /v1/assumptions`, cached for the session;
  - `POST /v1/simulate` and `POST /v1/compare`;
  - `POST /v1/transactions/parse` (the file is read in the browser and sent as text, never stored);
  - `POST /v1/saved` (signed in).
- Saved scenarios are **read** in the browser with `supabase-js` under RLS (PLAN.md §4). Saving goes through the API, which will call the atomic `save_scenario` function (`supabase/README.md`).

## 4. Chart library: Recharts 3 (recommended)

- **Keyboard:** "This is `false` by default in 2.x, and `true` by default in 3.0 and later". "When `accessibilityLayer` is true, then Recharts adds aria labels, roles, and keyboard controls to charts". The arrow keys move between points, and Tab does not step through every point. ([wiki](https://github.com/recharts/recharts/wiki/Recharts-and-accessibility))
- **Screen-reader caveat (documented by Recharts):**
  - VoiceOver users "need to turn QuickNav off".
  - JAWS/NVDA need "Forms Mode", which the layer's `role="application"` triggers.
  - So the chart is never the only route to the data. Every chart keeps the mocks' **one-sentence summary**, a **"Show the chart as a table"** alternative, and the visible **display rule** (`series_rule` from the engine).
- **Known open issue:** a reported bug says arrow keys don't move the tooltip while the mouse rests over the chart ([#7905](https://github.com/recharts/recharts/issues/7905)). It is low impact; the table alternative covers it.
- **Alternatives considered:**
  - **Observable Plot** sets ARIA labels ("The aria-label and aria-description attributes on the root SVG element can be set via the top-level **ariaLabel** and **ariaDescription** plot options") but offers no keyboard interaction ([Plot docs source](https://github.com/observablehq/plot/blob/main/docs/features/accessibility.md)).
  - **A hand-written SVG component**, like the mock's `chart.js` (~150 lines), is a viable fallback if Recharts' `role="application"` behaviour tests poorly with screen readers.
- **Chart rules kept from the mocks:**
  - y-axis from $0;
  - one axis;
  - value line plus a dashed "round-ups added" line;
  - direct labels at the line ends;
  - small multiples with a shared scale for comparisons;
  - colour never the only signal (labels "A"/"B" and line styles);
  - points pre-thinned by the engine (daily ≤ 366 days, weekly beyond), with the rule printed under the chart.

## 5. Signed-out vs signed-in

| | Signed out | Signed in |
|---|---|---|
| Run, compare, upload CSV | Yes | Yes |
| Save, re-run saved, delete | No: "Sign in to save" (magic link) | Yes |
| Saved scenarios page | Sign-in prompt ("You can run simulations without an account…") | List from Supabase (RLS: own rows only) |
| Data sent to the API | No token | `Authorization: Bearer <access token>` on `/v1/saved` only |
| Server-side identity checks | — | `supabase.auth.getClaims()`. Supabase: "*Never* trust `supabase.auth.getSession()` inside server code" ([docs](https://supabase.com/docs/guides/auth/server-side/nextjs)) |

## 6. Error and empty states (plain language, from the API's `error.message`)

| Situation | What the user sees |
|---|---|
| 422 validation / CSV problems | The API's message next to the field (`error.fields` → field highlight), with focus moved to the first problem |
| 422 `SIGN_CONVENTION_REQUIRED` | A choice: "In this file, are purchases positive or negative numbers?" |
| 413 too large | "This file is too large. The limit is 2 MB or 20,000 rows." |
| 429 | "Too many requests. Please wait {Retry-After} seconds." The button re-enables when the wait ends |
| 401 on save | "Your sign-in has expired. Sign in again to save." Results stay on screen |
| 503 `STORAGE_UNAVAILABLE` | "Saving isn't available right now. Your results are still here." |
| 5xx / network | "Something went wrong on our side. Please try again." plus the request id (`X-Request-ID`) in small print |
| No saved scenarios | The empty state from `saved` mock: "Nothing saved yet…" |
| No round-ups (all whole-dollar) | "These purchases were all whole-dollar amounts, so there was no spare change to invest." (gain % shows "n/a") |

All messages are announced through an `aria-live="polite"` region; destructive actions (delete) use a confirm dialog with focus management like the mock's assumptions dialog.

## 7. Testing plan

| Layer | Tool | What | Source |
|---|---|---|---|
| Unit / component | **Vitest + React Testing Library** (`vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/dom vite-tsconfig-paths`) | `format.ts` (separators, signs, no arithmetic); `api.ts` error mapping; `StatTiles`, `Headline`, `Disclaimer` render exact API strings; `ValueChart` renders summary + table + rule; label present on every results view | [Next.js Vitest guide](https://nextjs.org/docs/app/guides/testing/vitest). It notes Vitest "currently does not support" `async` Server Components, so those are covered end-to-end |
| End-to-end | **Playwright** (`@playwright/test`) against `next start` + the real API locally | (1) generate → results → compare; (2) CSV upload with a sign-convention prompt → results; (3) signed-out save prompt; (4) signed-in save → saved list (against a test Supabase project, Part 2) | — |
| Accessibility | **`@axe-core/playwright`** (`new AxeBuilder({ page }).analyze()`) on every page in light/dark × desktop/mobile, plus the keyboard walk from `web/mocks/a11y_check.py` (skip link first, visible focus, chart arrow keys, dialog Esc/focus return) | Zero violations is a merge gate | [axe-core-npm README](https://github.com/dequelabs/axe-core-npm/blob/develop/packages/playwright/README.md) |
| Copy safety | Unit test | Every results view renders the exact label and short disclaimer; a forbidden-phrases list ("you will", "guaranteed", "best strategy", "should invest", "forecast:" …) is absent from all UI strings | — |
| API contract | Existing API suites | Unchanged; the frontend uses only documented fields | — |

## 8. What Part 2 also changes in the API

- CORS for the single allowed origin.
- `/v1/saved` calls `POST /rest/v1/rpc/save_scenario` (atomic) instead of two inserts.
- An optional `?buys=summary` mode, because the full buy list (≈ 4,000 rows over 14 years) is most of a large response and the screens show only counts.
