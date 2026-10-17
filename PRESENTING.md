# Presenting RoundUp (7 to 10 minutes, about ten people in an AI-builder cohort)

For the presenter. The numbers were measured on 2026-10-16 (see "Numbers I can quote"). **Anything marked `[YOURS TO EDIT]` is a statement about you, your choices or your own experience that I could not confirm from the project files: confirm it, change it, or delete it before you say it.** Everything else is a fact about the app, checked against the code, tests and notes.

## The one thing to get right

**No real market data is used anywhere in the app.** Every price you will see is made up by a seeded model ("synthetic scenarios"). Say it in the first minute and again at the end.

**There is no data-licensing blocker for this demo.** Because the prices are invented, no one's data is being stored or shown, so no licence is needed for what you are presenting. Say that plainly; do not let it sound as if the demo is held back by a licence.

**Real data would need a licence first.** The data providers researched for this project (`DATA-SOURCES.md`) do not let you store their prices and show them on a public site on a free plan, and the plans that allow it cost hundreds of dollars a month or are quote-only (for example Tiingo's free plan forbids storing the data and lists redistribution from about $250 a month; EODHD's terms prohibit displaying it). No licence has been obtained and nothing has been signed. That is why real prices are not used, and why they are a separate step if this ever goes beyond a demo. `[YOURS TO EDIT: whether you have contacted any provider; the draft emails are in drafts/ and OQ-1 is still open in the notes.]`

**Why it is a time-limited, invite-only demo** (the reasons are practical, not legal or data-related):
- It runs on free tiers with usage limits (Vercel Hobby, Supabase Free).
- The rate limiting is kept in memory on each server instance, so it is a courtesy, not a hard cap.
- The Supabase free plan has no backups and pauses a project that is idle.
- Sign-ups are switched off, so no strangers' accounts or data are collected.
- Nothing monitors it. `[YOURS TO EDIT: the notes in OPERATIONS.md describe planned monitoring, but you have told me nothing watches it; say what is true.]`
- The privacy and disclaimer wording has not had a legal review (`SECURITY-PRIVACY.md` says so at the top).

**Who can do what today:** anyone who has the link can already run simulations and upload a file (processed in memory, not stored). Only saving a scenario needs an invited account. The preview addresses are public but unlisted.

Also say, once, early: **it is an educational demo, not advice and not a forecast; no money moves; there are no fees or taxes in the model.**

## Suggested running order (about 9 minutes)

| Min | What | Notes |
|---|---|---|
| 0:00 to 0:45 | The idea | "Round-up investing": a purchase of $4.37 rounds up to $5.00 and the 63 cents is set aside and invested. The demo answers one question: *what would the spare change have turned into in a made-up market?* Synthetic data, and why (above). |
| 0:45 to 2:45 | Live demo | The 2-minute script below. |
| 2:45 to 4:00 | Architecture (one slide) | Draw or show the diagram below. Three boxes and one rule: the browser never calculates money. |
| 4:00 to 6:00 | Engineering decisions | Pick three or four of the six below; do not read all of them. |
| 6:00 to 7:30 | What failed and what I learned | Pick two or three stories below. This is the part people remember. |
| 7:30 to 8:30 | Known limits | Say them before someone asks. |
| 8:30 to 10:00 | Questions | Likely questions below. |

If you have only 7 minutes: drop the engineering decisions to two and the failures to two.

## The 2-minute live demo (use the preview address; have the screenshots in `web/screenshots/redesign/after/` open in another tab as a fallback)

Before you start: open the site, check the top strip says "Synthetic scenario. Not a real fund, not real prices, and not a forecast."

1. **Typical spending (50 seconds).** Choose *Typical spending*. Say: "I do not need a bank file: I say how many purchases I make in a typical week." Leave 10 a week and the average round-up at $0.50. Pick *Crash and recovery* (a made-up market that grows, falls sharply, recovers). Run it.
   - On the results page point at the big number, then the **hand-checkable fact**: 10 purchases a week over 2015 to 2024 is **5,217 purchases**, and 5,217 x $0.50 = **$2,608.50** of round-ups, which is exactly the "Round-ups added" card. "The browser did not calculate that; the server did, and I can check it on a phone."
   - Point at the red or green growth figure: it has a sign and an arrow, because red and green are the colours people with red-green colour blindness confuse most.
   - Point at the dashed line (money put in) against the solid line (value), and at the "lowest point compared with money put in" sentence.
2. **A real-looking bank file (40 seconds).** Go back, choose *Upload a CSV*, pick `samples/sample-transactions.csv` (93 made-up rows). The app asks how amounts are signed, which is on purpose: it will not guess. Choose "Purchases are positive numbers", press *Check this file*: "93 of 93 rows can be used", with the pending and cancelled rows called out. Set the dates 2024-01-02 to 2024-03-29 and run: **86 purchases used, 7 ignored, $38.70** of round-ups (these figures are in `samples/expected.json`, which a test checks).
3. **Compare (20 seconds).** Press *Compare with another way of investing*, press *Compare*. Say: "Two ways of investing the same round-ups. The difference is shown in neutral colours on purpose: red or green there would look like telling you which is better."
4. **Light and dark, then stop (10 seconds).** Press the theme button. Scroll slowly so the cards come in. If someone has reduced motion turned on, nothing moves.

Do **not** sign in live: sign-in sends a real email and the demo is invite-only. If asked, say saving scenarios works (it was tested with real magic-link sign-in) and show `web/screenshots/redesign/after/saved-list-light.jpg`.

If the network fails: show the screenshots; the engine and the website also run on a laptop (`README.md`).

## One-slide architecture

```
  Browser (Next.js, React)                  FastAPI service (Vercel, Python)              Supabase
  ------------------------                  --------------------------------              --------
  Draws what the API sends.    JSON         Checks every input strictly.                  Email magic-link sign-in
  NEVER adds, rounds or        -------->    Builds the scenario (typical spending         Saved scenarios, row-level
  compares money. A test       <--------    or CSV rows).                                 security (users see only
  fails the build if it does.               Calls the engine.  ------------+              their own rows)
                                                                           v
                                              ENGINE (pure Python, no web code)    <---- same inputs ---->  INDEPENDENT second
                                              Decimal and exact fractions, integer cents;                   implementation, written
                                              every rule has an ID (FINANCE-RULES.md)                       from the rule text only
                                              Synthetic market model (seeded)                               (crosscheck/)
```

Say: "Three layers, one rule. The engine knows nothing about the web. A second program, written separately from the same written rules, checks the first one. The browser is only a drawing board."

Also on the slide, small: Hosting is Vercel Hobby (two preview projects, not production) and Supabase Free. CI runs everything on every push.

## Key engineering decisions

1. **An engine independent of the interface.** The money rules live in a Python package with no web code, so they can be tested alone and the interface can change (it was redesigned twice) without touching a number.
2. **A second implementation to cross-check it.** A separate program (`crosscheck/`) was written from the rule text only (a fresh AI agent, no access to the engine code) and the two are compared on 70 hand-made fixtures plus over two thousand random scenarios; they must agree exactly at display precision. Where they disagreed, the fix started from the rule text, not from either program. Be honest about its limit: it is a second reading of the same spec, so it catches coding mistakes and ambiguous wording, not a wrong rule.
3. **Test-first, hand-worked golden cases.** The expected numbers for the small scenarios were worked out by hand (and five of them checked in a spreadsheet by you `[YOURS TO EDIT]`) before the code produced them. Property tests (Hypothesis) and fault injection back them up: 55 deliberate rule-breaking mutations of the code, and the tests must catch every one (they do).
4. **Never calculating in the browser.** A static test scans the web source and fails the build if it finds arithmetic on money. Every figure on screen is the string the server sent. Even the "count-up" on the big number rolls the digits of the server's own string.
5. **Accessibility and geometry tests.** axe on every screen in light, dark and phone width; keyboard tests; and a layout checker that measures real boxes in the browser and fails on overlap, clipped text or anything off screen. All motion switches off under "reduce motion".
6. **Honest labelling.** Every page says "synthetic scenario, not a real fund, not real prices, not a forecast"; typical spending is always labelled an estimate; colours describe results in the made-up market only and never mean "buy" or "sell".

## What failed, and what I learned

- **A rounding bug the cross-check found.** The second implementation disagreed with the engine on a value that landed exactly on a half cent. The rule says half-even rounding, and the engine handled that one case wrongly (see `TEST-STRATEGY.md`, R-0.4). The disagreement process (go back to the rule text, not to either program) fixed it. Lesson: ties are where money code breaks, and a second reading finds what a first reading is blind to.
- **A CSV layout bug that no test could see.** On the first real preview the CSV step had overlapping controls. Every test passed, because none of them measured where things were drawn. You found it by using the page `[YOURS TO EDIT]`. It led to the geometry checker. Lesson: test what the user sees, not only that elements exist.
- **The same layout fix failed on CI.** Text was 279 px wide on macOS and 284 px under Linux, so a dropdown that fitted on the laptop clipped in CI. It was reproduced in a Linux container; the dropdowns were replaced the dropdowns with wrapping radio lists and the checker got a safety margin. Lesson: layout results are not portable between operating systems.
- **CI was red on three pushes in a row.** One requirements file was written in the form Vercel's installer wants (`name @ ./path`), which pip rejects. Fix: a second file for CI and a guard test that installs both in clean environments. The first diagnosis missed the real error because only the end of the log was read. Lesson: read the whole error.
- **A bank-file bug.** The pending rows were being counted (71.50 instead of 70.90) because the page never sent the Status column. Found by running a real export through it `[YOURS TO EDIT: it was your own bank export in the project notes]`.
- **A deployment surprise.** The first deployment of a Vercel project becomes a production deployment even without the production flag. It went live by accident, was removed, and every deployment now says `--target=preview`.
- **A scenario that contradicted its own label.** The "Sideways" market was meant to have no overall trend, but the seeded series fell to 0.31 of its start. It showed up when its mini chart was drawn on a shared scale. The model now pulls it back toward its start, inside a stated band, and a test enforces the band for the published seed and for 60 other seeds.
- **Duplicate files from folder sync.** The folder was on a synced desktop and the sync made " 2" copies of files; two were committed by accident. The repository now ignores them and will move out of the synced folder.

## Known limits (say them first)

- **No real market data**, so nothing here says how any real fund behaved. The scenarios are illustrations of kinds of behaviour.
- **Not advice, not a forecast, no fees and no taxes.** Real round-up apps may charge fees that matter a lot for small balances.
- **Typical spending is an estimate from averages**; real spending varies. Uploaded files are read in your session and not stored.
- **A time-limited, invite-only demo for practical reasons:** free tiers with usage limits; per-instance, in-memory rate limiting; the Supabase free plan has no backups and pauses when idle; sign-ups are off; nothing monitors it; no legal review of the privacy and disclaimer wording. Anyone with the link can already run simulations; only saving needs an invited account. None of this is a data-licensing issue: the demo uses no real data.
- **The "ask about these numbers" AI explainer is not built.** The results page says "Coming later". Do not demo it.
- **Accessibility:** automated checks, keyboard tests and an independent review, but not a real screen-reader session and not a person with colour-vision deficiency. Colour-blindness was checked by simulation only.
- **Linux text rendering** is checked in CI; the Linux container was not run locally for the latest changes.
- **The second implementation shares the spec** with the first, so it cannot catch a wrong rule, only a wrong reading.
- **Hand calculation** was checked on five worked examples, not on everything `[YOURS TO EDIT: that you did the spreadsheet check]`.

## Likely questions, honest answers

- **Why not use real data, even just for a demo?** Because it would need a licence first. The providers researched for this project forbid storing and publicly showing their prices on a free plan, and the plans that allow it cost hundreds a month or are quote-only. The demo does not need real prices to show how round-ups, timing, dividends and splits behave, so it uses a synthetic model and there is no licensing problem to solve. If a provider answered my questions, real history could come later. The rules for real series (raw closes, splits, dividends) are written down (`FINANCE-RULES.md`, R-7), but no real data has ever been loaded or tested. `[YOURS TO EDIT: whether you say "I looked at" them yourself, and what you did or did not ask them]`
- **So why is it invite-only and temporary?** Practical reasons, not data or legal ones: free tiers with limits, no backups, the database pauses when idle, nobody is watching it, and the privacy and disclaimer wording has had no legal review. Anyone with the link can run simulations today; only saving needs an invited account, and sign-ups are off.
- **Is this financial advice?** No. It says so on every page and the colours never mean "buy" or "sell". It does not recommend a strategy or predict anything.
- **How do you know the numbers are right?** Three independent angles: hand-worked cases (some checked in a spreadsheet), a second implementation written from the rules alone that must agree exactly, and tests that break the code on purpose to see whether they notice. None of this proves it is right for real markets; it shows the code does what the written rules say.
- **What did the AI do and what did you do?** `[YOURS TO EDIT: this is your answer to give.]` What the project files support: the code was written with Claude Code as the coding agent, stage by stage, with your approval at each stage; the second implementation and several reviews were done by separate AI agents that were shown only the written spec; the layout bug and the pending-row bug were found by you using the page (check that this is how you remember it). What they cannot tell me: how much of the planning and decision-making was yours, in your own words.
- **Why a Python engine and a separate web app?** So the money rules can be tested without a browser and the interface can change freely. It also keeps the "no arithmetic in the browser" rule easy to enforce.
- **Would you ship it?** `[YOURS TO EDIT: this is your opinion to give.]` A suggested answer: as an educational demo to invited people, it is already running; as a financial product, no. It would need real data under a licence, real fee modelling, a legal and compliance review of the wording, monitoring and backups, and a proper accessibility audit with real assistive technology.
- **What does it cost to run?** Free tiers of Vercel and Supabase for the demo (`OPERATIONS.md` has the estimate and the limits), which is also why it has no backups and pauses when idle. Not free at scale.
- **What would you do next?** `[YOURS TO EDIT]` Ask providers about a licence, a screen-reader and a colour-blind-user session, then the AI explainer, with a fixed set of questions that only describe the numbers.

## Numbers I can quote (measured 2026-10-16; re-check the day before)

- Engine, scenario model and cross-check agreement: 577 tests pass. Independent API tests: 514. API tests: 152. Fault injection: 55 of 55 mutations caught.
- Web: 212 component and unit tests (including the contrast and colour-blindness checks) and 63 end-to-end, accessibility, keyboard and performance tests, run in a clean checkout with the same commands CI uses.
- Contrast: every colour pair in both themes meets WCAG 2.2 AA (`DESIGN.md` section 10 lists the ratios).
- Performance (local): setup page about 646 KB uncompressed on first load, about 0.85 s to network idle on the laptop the tests ran on; deployed numbers are in `DEPLOY.md` section 7.
- Demo figures: 10 a week for 2015 to 2024 is 5,217 purchases and $2,608.50 of round-ups; the sample bank file gives 86 purchases used, 7 ignored and $38.70; 10 a week for 51 whole weeks is 510 purchases and $255.00.
