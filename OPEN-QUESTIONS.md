# RoundUp — Open Questions

**Revision 2 (2026-10-12).** These questions were answered by the owner and are now applied: a portfolio demo on Vercel Hobby; anonymous simulations; whole-dollar → $0; refunds create no round-up and never reverse one; posted date; invest at $5; reinvest by default with a toggle; VOO + SCHD from 2012; no legal review for the invite-only demo.

## A. Defaults chosen on your behalf: please confirm or change

You asked for the most conservative reasonable default on everything you did not answer. Each is stated in the file shown.

| # | Default | Where | Why conservative |
|---|---|---|---|
| D-1 | A dividend with no pay date is rejected; dates are never estimated | FINANCE-RULES R-8.8 | Never invents data or reinvests early |
| D-2 | No app or subscription fee modelled (disclosed) | R-10.4 | No unreviewed rules |
| D-3 | No annualized return (XIRR) | R-13.3 | Easily mistaken for a forecast |
| D-4 | Identical rows within a file: kept and flagged; overlapping files: matches excluded by default | R-4.2, R-4.3 | Never silently drops or double-counts |
| D-5 | A run fails at 4+ consecutive missing price days, or a missing price on any split/dividend day | R-6.3 | Prefers no answer over a wrong one |
| D-6 | Threshold fixed at $5.00 (not user-configurable); other strategies kept as comparisons | R-5.2 | Your rule; less test surface |
| D-7 | **Accepted with change:** the shared demo uses four **named synthetic market scenarios** (steady growth, crash and recovery, sideways, high volatility) from a documented seeded model, each labelled "Synthetic scenario. Not a real fund, not real prices, and not a forecast." Real-data mode stays local-only and provider-agnostic | SCENARIO-MODEL.md, DATA-SOURCES §5 | Quoted terms don't permit showing results from real data to others |
| D-8 | Merchant descriptions are never stored | SECURITY-PRIVACY §2 | Most sensitive field |
| D-9 | Sign-in by email magic link only | SECURITY-PRIVACY §3 | No third-party OAuth |
| D-10 | AI explainer for signed-in users only, fixed questions, $5/month hard cap | PLAN §4, OPERATIONS §3 | Abuse and cost control |
| D-11 | No backups (Supabase Free); users told saved scenarios are not backed up | OPERATIONS §6 | Near-free; only re-runnable data at risk |
| D-12 | Minimum age 18 | SECURITY-PRIVACY | Simplest privacy position |
| D-13 | Web and API as two Vercel Hobby projects (not the "Services" beta) | PLAN §4 | Avoids a beta dependency |
| D-14 | Supabase rather than InsForge | PLAN §4.1 | More mature, better-documented token verification; same free limits |

## B. Still open

| ID | Undecided | Why it matters | Next step | Blocks |
|---|---|---|---|---|
| OQ-1 | Whether Tiingo or EODHD permits a free, invite-only demo showing **simulation results only** | Decides whether the shared demo can use real VOO/SCHD history | You send [drafts/provider-emails.md](drafts/provider-emails.md) | Real data in the shared demo (sample data works without it) |
| OQ-2 | R-7.7 adjusted-series tolerance | Needed only when real data is ingested | Decide after the first real backfill | Real-data mode |
| OQ-3 | Whether a daily request keeps a Supabase Free project from pausing | Unverified in docs | Observe during Phase 4; otherwise accept manual restore | Nothing (demo tolerates it) |
| OQ-4 | Real cost per simulation on Vercel's Python runtime | Hobby has 4 CPU-hours/month | Measured locally (≈ 0.15 s, OPERATIONS.md); confirm in Vercel logs after the first deploy | Nothing |
| ~~OQ-5~~ | Chart library | — | **Resolved:** Recharts 3 (owner decision, stage 5), with our own keyboard layer | — |
| ~~OQ-6~~ | Hand calculations | — | **Resolved:** owner's spreadsheet matched HC-1..HC-5 | — |
| OQ-8 | Approval of the new on-screen wording | Wording was added to fix review findings | Review COPY.md "Added after the stage-5 web review" | Launch |
| OQ-9 | Keep or drop the "+64.78%" growth percentage | The reviewer called it borderline performance wording | Your call; dropping it is a display change only | Nothing |
| OQ-10 | Day-first dates (01/06/2020 = 1 June) in uploaded files | The engine reads only ISO and US month/day/year; the app now warns | Add a date-format option to the parse endpoint if invitees use non-US banks | Nothing for a US cohort |
| OQ-11 | Session across tabs after the magic link | The link opens a new tab; whether the first tab sees the sign-in depends on supabase-js syncing storage between tabs (not verified) | Check during the first-deploy smoke test (DEPLOY.md §4) | Nothing (reload + Saved works) |
| OQ-7 | Whether to show **real** VOO/SCHD results locally in a recorded walkthrough (e.g. a video for the cohort) | A recording shown to others is arguably display | Include in the provider emails' answers | Any recording using real data |
