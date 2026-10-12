# RoundUp — Open Questions

Each item states what is undecided, why it matters, the proposal (if any), and which phase it blocks. Nothing here is implemented until decided.

## A. Business and licensing (block Phase 2 and launch)

| ID | Undecided | Why it matters | Proposal | Blocks |
|---|---|---|---|---|
| OQ-1 | **Which market-data provider, under which licence.** | No provider publishes a free tier that allows storing **and** publicly displaying data. Display costs are $250/mo (Tiingo, price unverified), "from $399/mo" (EODHD, by quote), or $2,499/mo (Massive). This is ~85–90% of the launch budget. | Send the DATA-SOURCES.md §6 questions to EODHD and Tiingo (and ask Alpha Vantage and EODHD about educational/academic terms). Choose EODHD if the quote is ≤ ~$400/mo; otherwise Tiingo. | Phase 2 (development plan), launch (display licence) |
| OQ-2 | **Your monthly budget ceiling** for data + hosting. | It decides whether a public launch is viable now, or whether we run a private/closed beta first. | — | Launch |
| OQ-3 | **Will RoundUp ever be monetized** (subscriptions, ads, sponsorship)? Is it run by an individual or an organisation? | Vercel Hobby is "non-commercial, personal use only". Data licences distinguish personal, internal, commercial and display use, and Tiingo requires organisations to use Commercial plans. | Assume "commercial" for licensing to stay safe; budget Vercel Pro. | Launch |
| OQ-4 | **May anonymous (signed-out) visitors run simulations?** | It changes the licence question (display to anonymous users), abuse and rate-limit design, and the "Try it" flow. | Yes for simulations; no for the AI explainer. | Phase 3 |
| OQ-5 | **Target countries / jurisdictions.** | Determines data-protection obligations, the legal review scope, the financial-promotion analysis and hosting region. | Start with US-only users; region `us-east`. | Launch (legal review) |
| OQ-6 | **Minimum age.** | Privacy law and terms; a student audience is plausible. | 18+ in v1, unless legal review says otherwise. | Launch |

## B. Finance rules (FINANCE-RULES.md)

| ID | Undecided | Why it matters | Proposal | Blocks |
|---|---|---|---|---|
| OQ-7 | **R-8.8: what to do if the provider has no dividend pay dates** (Tiingo has none). | Reinvesting at the ex-date close uses cash before it exists, a small timing advantage. Estimating pay dates invents data. | Moot if EODHD is chosen. If Tiingo: reinvest at the first session ≥ ex-date + a fixed lag, disclosed, **or** source pay dates from issuer histories, if their terms allow. | Phase 2 dividend ingestion |
| OQ-8 | **R-7.7 cross-check tolerance** (our raw + events total return vs provider adjusted close). | Too tight blocks good data; too loose misses a dropped dividend. | Set from the first backfill: 2× the largest yearly difference observed on verified-clean years, with a ceiling of 0.05 percentage points. Confirm after seeing data. | Phase 2 acceptance |
| OQ-9 | **R-13.3: show an annualized money-weighted return (XIRR)?** | It is the correct annualized measure for irregular contributions, but hard to explain and easy to misread as a forecast. | Not in v1; revisit after user testing. | Phase 3 (UI) |
| OQ-10 | **R-10.4: offer an optional flat monthly app fee** in the simulation? | Real round-up apps often charge monthly fees, which can outweigh returns on small balances. It is a strong lesson, but it adds a rule. | Yes, as an off-by-default "subscription fee" input. It needs its own rules first (what is charged when cash is insufficient: sell fractional shares, or accrue a balance?) and another independent review. | Phase 1 (if yes) |
| OQ-11 | **Please confirm these decisions**, made explicitly but product-flavoured: whole-dollar purchase → $0 (R-2.2); refunds never reverse round-ups (R-3.1); identical rows within a file kept and flagged (R-4.2); overlapping files excluded by default (R-4.3); posted date used (R-1.2); default threshold $5 (R-5.2); default reinvest on (R-8.5); no interest on cash. | Each changes numbers users see. | As written. | Phase 1 |

## C. Product and scope

| ID | Undecided | Why it matters | Proposal | Blocks |
|---|---|---|---|---|
| OQ-12 | **Which two funds:** VOO or VTI (broad); SCHD or VYM (dividend). Or offer all four? | All four predate 2012 and have verified inception dates. Licence pricing may be per symbol. More funds means more comparisons and more testing. VOO had a reverse split in 2013 and SCHD a 3-for-1 in 2024, so both exercise split handling. | Offer all four if the licence price is the same. Otherwise VOO + SCHD (most widely recognised; both exercise splits). | Phase 2 |
| OQ-13 | **AI explainer: fixed questions only, or free text?** | Free text multiplies the adversarial surface, eval size and cost. | Fixed questions in v1. | Phase 5 |
| OQ-14 | **Offer an opt-in to store merchant descriptions** with saved transactions? | It is useful for re-importing and checking duplicates, but it is the most sensitive field. | No in v1. | Phase 4 |
| OQ-15 | **Sign-in methods:** email magic link, Google, both? | Support load and privacy. | Magic link + Google. | Phase 4 |
| OQ-16 | **Chart library** (e.g. Recharts, visx, Observable Plot). | Accessibility (keyboard crosshair, SVG), bundle size. | Evaluate 2 in a 1-day spike in Phase 3 against DESIGN.md §6. | Phase 3 |
| OQ-17 | **API host: Render ($7/mo) or Fly.io (~$2–5/mo).** | Small cost difference; Render is simpler to operate. | Render. | Phase 3 |

## D. Process

| ID | Undecided | Why it matters | Proposal | Blocks |
|---|---|---|---|---|
| OQ-18 | **Who writes the independent cross-check implementation and the spreadsheet** (TEST-STRATEGY.md §4)? | Independence is the point. If the engine author also writes the cross-check, shared misunderstandings go undetected. | A separate AI session that is given only FINANCE-RULES.md and the fixture format writes the `Fraction` script. **You** (or another person) build the 3-scenario spreadsheet. | Phase 1 acceptance |
| OQ-19 | **Legal reviewer** for the disclaimer, privacy policy, terms and the financial-promotion question. | Required before launch (SECURITY-PRIVACY.md §10). | — | Launch |
