# RoundUp design mocks (for review)

Static, clickable screens built to DESIGN.md. **Every number comes from real API responses:** `build_mock_data.py` calls the real FastAPI app, which runs the real engine on the real synthetic-scenario generator, and writes `data.js`. Nothing is typed by hand. These are not the production site.

Open `index.html` in a browser (no server needed). Regenerate:
- data: `PYTHONPATH=engine/src:api .venv/bin/python web/mocks/build_mock_data.py`
- screenshots: `.venv/bin/python web/mocks/capture.py`
- checks: `.venv/bin/python web/mocks/a11y_check.py`

## Screens and screenshots (`screenshots/`)

| Screen | Desktop (1280 px) | Mobile (390 px) |
|---|---|---|
| Scenario setup | `setup-desktop.png` | `setup-mobile.png` |
| Results | `results-desktop.png`, `results-desktop-dark.png` | `results-mobile.png` |
| Side-by-side comparison + assumptions panel | `compare-desktop.png` | `compare-mobile.png`, `compare-mobile-assumptions-open.png` |
| Saved scenarios | `saved-desktop.png`, `saved-desktop-empty.png`, `saved-desktop-signed-out.png` | `saved-mobile.png` |

## Colours (light / dark), and why

| Token | Light | Dark | Use and reason |
|---|---|---|---|
| `--surface` | `#fcfcfb` | `#1a1a19` | Page background: warm off-white or near-black, calmer than pure white or black |
| `--panel` | `#f3f2ee` | `#232321` | Label strip, assumptions panel: quietly separates context from results |
| `--ink` | `#0b0b0b` | `#f0efec` | Body text: **19.17:1 / 15.15:1** |
| `--ink-2` | `#52514e` | `#c3c2b7` | Secondary text and axis labels: **7.73:1 / 9.72:1** (7.09:1 on the panel) |
| `--link` | `#1f62b5` | `#6ea8f0` | Links and primary buttons: **5.89:1 / 7.07:1**. White on `#1f62b5` is 6.05:1 and `#0b0b0b` on `#6ea8f0` is 7.99:1. **Changed from DESIGN.md's `#2a78d6`**, which fails as text (4.30:1, and 4.42:1 for white on it) |
| `--series-1` | `#2a78d6` | `#3987e5` | Value line / strategy A. Non-text contrast **4.30:1 / 4.79:1** (needs ≥ 3:1). From the validated palette |
| `--series-2` | `#eb6834` | `#d95926` | Strategy B. **3.12:1 / 4.48:1**. Validated CVD-safe pair with series-1 (stage 1) |
| `--added` | `#52514e` | `#c3c2b7` | Dashed "round-ups added" line: neutral, so it reads as a reference, not a second result |
| `--control` | `#8a8984` | `#8a897f` | Form-control and option-card borders: **3.41:1 / 4.95:1** (WCAG 1.4.11 needs 3:1). `--line` (`#e4e3df`, 1.25:1) is used only for decorative dividers |
| `--notice-bg` / border | `#fff6e0` / `#b98a00` | `#2b2513` / `#c99a1a` | The disclaimer box: noticeable but not alarming. Text on it is 18.29:1 |

**Gains and losses use the same ink.** There is no green/red, and direction is shown by "+"/"−" and words (DESIGN.md principle 4), so nothing nudges toward a choice.

## Type scale, and why

| Size | Use |
|---|---|
| 28 px / 650 | Page title (one per page) |
| 26 px / 650 | Stat tile values: the four numbers people look for first |
| 22 px | Headline sentence: the result in plain words, before any chart |
| 20 px / 650 | Section headings, step legends |
| 16 px / 1.5 | Body text, controls (never smaller for anything you must read to act) |
| 14 px | Secondary notes, chips, assumptions text, table cells |
| 12–13 px | Chart axis and line labels (drawn at the real screen width, so they stay 12 px on phones) |

Font: Inter, with system fallbacks. All numbers use tabular figures, so columns line up.

## Chart choices, and why

- **Value line + dashed "round-ups added" line**, on one axis starting at $0. The gap between the two lines *is* the difference. There is no dual axis and no stacking.
- **Display rule printed under every chart**, exactly as the engine sends it (`series_rule`): "Chart shows daily values for ranges up to 366 days and one value per week (the week's last trading day) for longer ranges. All figures are calculated daily."
- **Comparison = small multiples** with a **shared scale**, stated in the caption, not two lines on one chart. Each panel is labelled A or B, so colour is never the only cue.
- Direct labels at the line ends, a legend, a recessive grid, 2 px lines and round y-axis ticks (1/2/5 × 10ⁿ).
- **Every chart has** a one-sentence text summary (`aria-label`), keyboard reading (focus the chart, then use ←/→, Home/End, PgUp/PgDn; values are announced through a live region) and a "Show the chart as a table" alternative.

## What I checked, and how

| Check | Method | Result |
|---|---|---|
| Text and non-text contrast | Computed WCAG 2.x ratios for every token pair (table above). axe-core also checks rendered text contrast | All pass AA; one token changed (`--link`) |
| Automated WCAG 2.2 A/AA + best practice | axe-core 4.10.2 in the installed Chrome via Playwright, on 4 pages × desktop / mobile / dark | **0 violations** in all 12 runs (after fixing one landmark and two heading-order issues) |
| Keyboard order | Tabbed through every page (`a11y_check.py`) | First stop is "Skip to main content" on every page; every stop shows a visible 2 px focus outline (0 without); radio groups are single stops (arrow keys inside) |
| Chart keyboard | Focus chart, then Home, then → | The announced value changes (results and compare) |
| Assumptions dialog (mobile) | Enter opens, Escape closes | Opens, closes, and focus returns to the "Assumptions" button |
| Targets | CSS | Buttons, nav links and option cards are at least 44 px tall |
| Reduced motion | CSS | No animations; `prefers-reduced-motion` honoured |

Not checked: a real screen reader (VoiceOver/NVDA) pass, and Windows High Contrast / forced-colours mode. Both are planned for Part 2 on the real site.

## Wording exactly as shown

- **Label strip (every page):** "Synthetic scenario. Not a real fund, not real prices, and not a forecast."
- **Disclaimer box (results and compare, above the numbers):** "**Hypothetical simulation on a synthetic market.** These results show how sample round-ups behave in a made-up market scenario. No money was invested, the prices are not real, and this is not a forecast. It is not investment, tax or financial advice."
- **Assumptions panel footer:** the API's disclaimer text: "Hypothetical simulation on a synthetic market. No money is invested, the prices are not real, and these results are not a forecast or financial advice. Taxes, inflation and interest on uninvested cash are not included."
- **Results headline:** "In this made-up scenario, **$1,789.92** of sample round-ups ends at **$2,949.37** on Dec 31, 2024: **$1,159.45** more than was put in."
- **Chart caption:** the engine's display rule, then "Scenario dates follow a real calendar, but the prices are made up."
- **Saved scenarios:** the label strip, plus "Every saved result comes from a synthetic scenario: not a real fund, not real prices, and not a forecast."
- **Footer:** "RoundUp is an educational demo. No money moves and nothing here is advice or a forecast."
- **Comparison note:** "'B compared with A' is B minus A. These differences come from this one made-up scenario and say nothing about which choice works better in general."

## Independent critique, and what changed

A separate reviewer agent saw only the screenshots, the HTML, `app.js` and DESIGN.md. It was asked about clarity, accessibility, and wording that could read as advice or a forecast.

| # | Finding | Severity | Resolution |
|---|---|---|---|
| 1 | Saved scenarios show results with no label or disclaimer | High | **Fixed:** label strip and a synthetic-scenario sentence on the saved page; "Synthetic scenario: …" on each card |
| 2 | Compare table cut off on mobile | High | **Fixed:** below 600 px each figure becomes a stacked block (A, B, "B minus A") |
| 3 | "Your … would have been worth", and real calendar dates, read as real history | High | **Fixed:** H1 "Your sample round-ups in a made-up market"; headline "In this made-up scenario, $X of sample round-ups ends at $Y…"; notice "show how sample round-ups behave…". **Kept** calendar dates (the engine runs on a trading calendar), but every chart and the setup screen now say "Scenario dates follow a real calendar, but the prices are made up." |
| 4 | Assumptions describe real prices, funds and hindsight | High | **Fixed at the source** (API `content.py`): "each simulated day's closing price from the scenario"; running costs "treated as already included in the scenario's prices"; R-11.3 now reads "A made-up scenario shows one possible path, not what any market will do." |
| 5 | "Purchases" means both card spending and buys | High | **Fixed:** "from 3,606 sample purchases" vs "Money was invested 325 times from round-ups…"; compare rows "Times invested from round-ups / dividends" |
| 6 | "Cash not yet invested" is wrong for kept dividends; "Difference" used twice | High | **Fixed:** row "Cash not invested (round-ups waiting, plus dividends kept as cash)"; column "B minus A"; row "Value minus round-ups added", plus a note explaining why two rows have the same gap. **Deferred:** splitting cash into two separate figures needs two engine fields (proposed for Part 2), because the frontend must not subtract |
| 7 | Definitions only in hover titles | Medium | **Fixed:** each tile label is a real button (`aria-expanded`) that shows visible definition text. Tile wording updated |
| 8 | Mobile nav hides items in a sideways scroll | Medium | **Fixed:** nav wraps onto two rows |
| 9 | Mobile Assumptions button and dialog | Medium | **Fixed:** sticky button; dialog has a sticky header with title and Close at the top; focus moves to the dialog heading on open and returns to the button on close (verified) |
| 10 | Disclaimer repeated too often (and duplicated in one paragraph) | Medium | **Fixed:** the API disclaimer no longer repeats the label; the chart caption no longer restates the scenario label |
| 11 | "Default" tag and style wording read as a recommendation | Medium | **Fixed:** "Starting setting" (UI and API assumption R-5.2), "All four are equally valid to explore"; style descriptions now "In this model: …"; "made-up markets"; "Sample number (same number, same purchases)"; "Dividends (simulated)" |
| 12 | Chart summary assumes a rise; live region floods; long table | Medium | **Fixed:** neutral summary ("goes from … to …, with ups and downs"); announcements throttled (250 ms). **Deferred:** naming the lowest point needs an engine-provided figure (proposed for Part 2). The table stays one row per chart point, matching the chart |
| 13 | Compare axis tops out at $5,000; panels start at different years | Medium | **Fixed:** steps of 1/1.5/2/2.5/3/4/5 × 10ⁿ (now $4,000); year labels start at the first year in every panel |
| 14 | Disabled AI buttons are unreachable by keyboard | Medium | **Fixed:** `aria-disabled="true"` (focusable, described by the "not available" note) |
| 15 | Dark-mode "Sign in to save" contrast | Medium | **Checked, not changed:** rendered colours are `#0b0b0b` on `#6ea8f0`, which is **7.99:1** |
| L | Technical meta line in the main flow | Low | **Fixed:** moved into a "Technical details" disclosure |
| L | Unlinked rule IDs | Low | **Fixed:** one "How these rules work" link per panel. Linking every ID added 13 tab stops |
| L | Mock-state buttons look like filters | Low | **Fixed:** labelled "Design preview only" |
| L | Chips hard-coded | Low | **Fixed:** read from the recorded request settings |
| L | Bold "more" reads celebratory | Low | **Fixed:** only the amounts are bold |
| L | Saved-card details; delete confirmation; Account link | Low | **Fixed:** cards show date and engine version; Account link no longer points to saved. Delete confirmation is specified for Part 2 (FRONTEND.md §6) |
| L | "64.78%" over-precise | Low | **Declined:** it is the engine's figure, and rounding it in the browser would be frontend arithmetic. Can be revisited as an engine display option |

After the changes: axe-core still reports **0 violations** on all 12 page/mode runs; keyboard, chart and dialog checks pass.
