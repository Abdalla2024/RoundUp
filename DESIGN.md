# RoundUp — Design Brief

**Feel:** calm, clear, trustworthy. Like a well-made bank statement crossed with a science explainer. No hype, no confetti, no green "you're winning" colours, no countdowns. Every number has a label in plain words and a way to find out where it came from.

## 1. Principles

1. **One question per screen.** Setup asks "what are we simulating?". Results answer "what would have happened?". Compare answers "what difference does this choice make?".
2. **Numbers before charts.** The headline is a sentence with three numbers. The chart supports it.
3. **Assumptions are never more than one click away.** Every result card links to the assumption it depends on.
4. **Neutral about outcomes.** Gains and losses use the same ink. Direction is shown with words and signs ("+$41.20", "−$3.10"), not red and green. The product must not nudge anyone toward a fund.
5. **The disclaimer is part of the layout**, not hidden fine print (SECURITY-PRIVACY.md §9).

## 2. Layout

- Desktop: a single centred column, max 1,120 px. Results use a 2-column grid: main content, with the **assumptions panel** as a right rail (320 px).
- Mobile (≥ 360 px): a single column. The assumptions panel becomes a bottom sheet opened by an "Assumptions" button that is always visible.
- Top bar: logo, "How this works", "Saved scenarios" (signed in), and account. Under it, a persistent thin line on result screens: *"Synthetic scenario · Not a real fund, not real prices, not a forecast"* (demo; see SECURITY-PRIVACY.md §9).
- Generous whitespace: 8 px spacing scale (8/16/24/32/48). Cards have a 1 px border and no heavy shadows.

## 3. Key screens

### 3.1 Scenario setup
- Step 1 **Transactions**: three choices as large cards: "Generate sample spending" (pick a profile such as Student, Commuter or Family, and a period), "Upload a CSV" and "Use last saved".
- Upload opens a column-mapping step, then the **import summary**: "312 purchases used · 18 rows ignored (14 card payments, 4 refunds) · 2 possible duplicates". Each count expands to the rows behind it.
- Step 2 **Market scenario**: a card per synthetic scenario (Steady growth, Crash and recovery, Sideways, High volatility) with a one-line description, a small preview line, and the label "Synthetic scenario. Not a real fund, not real prices, and not a forecast." Then pick a style (broad-market or dividend). No tickers or fund logos ever appear (D-7).
- Step 3 **How round-ups invest**: a timing choice (next trading day / weekly / monthly / every $5) and a "Reinvest dividends" toggle (default on). Each option has a one-line explanation.
- Step 4 **Dates**: start and end within the data's coverage. Invalid dates are explained ("This scenario starts on 3 Jan 2012").
- Primary button: "Run simulation". The setup collapses into a summary chip row above the results ("312 purchases · Steady growth, broad style · Next trading day · Dividends reinvested · Jan 2015 – Sep 2026 · Edit").

### 3.2 Results (one fund, one strategy)
- **Headline sentence:** "Your **$1,284.37** of round-ups would have been worth **$2,019.88** on Sep 30, 2026, a difference of **+$735.51**." (Illustrative numbers only.)
- **Stat row** (4 tiles): Round-ups added · Value at end · Dividends earned · Difference. Each tile has a "?" tooltip with the definition from §7.
- **Chart:** value over time (line) against total round-ups added (step line, neutral grey). Dividend markers are small ticks on the x-axis. Tooltip shows date, value, added to date and dividends to date.
- **Flags box**, only if relevant: "3 purchases were bought a day later because of a missing price."
- "Explain this" buttons (fixed questions) under the chart. The AI's answer appears in a quiet panel labelled "AI explanation of these numbers".
- **Table view** toggle: monthly rows (added, bought, dividends, value).

### 3.3 Side-by-side comparison
- Up to 4 columns, one per fund × strategy, each with the same stat rows so values align horizontally. Differences are shown relative to a chosen baseline column ("+$12.40 vs baseline").
- **Chart:** small multiples, one panel per fund with a shared y-axis, showing a single value line plus the grey "added" line. No dual axes, and no more than 3 coloured series in any one chart.
- A one-line, neutral "What's different" note per column, generated from the configuration, not by the AI ("Buys once a week instead of the next trading day").

### 3.4 Assumptions panel (right rail / bottom sheet)
- Grouped, collapsible, in plain language, each with a link to the matching rule in "How this works":
  - Rounding (whole-dollar purchases add $0)
  - When money is invested
  - Prices used (closing price, no adjustments)
  - Dividends (when earned, when reinvested)
  - Fees (the expense ratio is already in the price; trading costs are not included)
  - Not included (taxes, interest on cash, app fees)
  - Hindsight ("These funds were chosen because they're well known today")
  - Data source and "as of" date, dataset version
- Anything the user changed from the default is marked "Changed".

### 3.5 Saved scenarios
- A list of cards with name, chip summary, last run date and data "as of" date. Actions: Open, Re-run with latest data, Rename, Delete.
- If newer data or a correction exists, a quiet notice says "Newer market data available. Re-running may change the numbers."
- Empty state: "Nothing saved yet. Run a simulation and choose Save."
- Account page: "Download my data", "Delete account" (two-step confirmation that states exactly what is deleted).

## 4. Typography

- **Inter** (Google Fonts) for UI and text, with `font-variant-numeric: tabular-nums` on every number so columns line up. Fallback: the system UI font.
- Scale: 14 (labels) / 16 (body) / 20 (section) / 28 (headline sentence) / 36 (stat values). Line height 1.5 for body.
- Sentence case everywhere; no all-caps.
- Money always has a currency symbol, two decimals and thousands separators. Share counts have up to 6 decimals in tables only.

## 5. Colour

Defined as CSS tokens on `:root`, with dark mode redefined under `prefers-color-scheme: dark` and a `data-theme` override.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--surface` | `#fcfcfb` | `#1a1a19` | page and chart background |
| `--ink` | `#0b0b0b` | `#f0efec` | primary text |
| `--ink-2` | `#52514e` | `#c3c2b7` | secondary text, axis labels |
| `--line` | `#e4e3df` | `#33332f` | borders, grid (recessive) |
| `--accent` | `#2a78d6` | `#3987e5` | links, focus, primary button |
| `--series-1` | `#2a78d6` | `#3987e5` | first fund |
| `--series-2` | `#eb6834` | `#d95926` | second fund |
| `--series-3` | `#1baf7a` | `#199e70` | third series, if ever needed |
| `--added` | `--ink-2` at 60% | same | "round-ups added" reference line |

- Series colours are assigned **by fund in a fixed order** and never change when filters change (fund A is always slot 1).
- The palette was **validated** with the dataviz validator. Light: CVD ΔE worst adjacent 9.2, normal-vision 27.6. Dark: 9.4 and 26.5. All pass. `--series-3` is below 3:1 contrast on the light surface (2.74), so it is only used with direct labels and the table view.
- Status colours (warning or info for data notices) are separate from the series colours and always appear with an icon and text.
- No red/green for gains and losses (principle 4).

## 6. Charts

- Forms: a line for value over time; a step line for cumulative round-ups added; small multiples for comparison; stat tiles for headline numbers. No pie charts, no dual axes, no 3D.
- Marks: 2 px lines, 8 px hover markers, recessive grid (horizontal only), y-axis starting at $0 for value charts.
- Direct labels at the line ends ("Steady growth", "Added"), plus a legend when there are ≥ 2 series.
- Hover: a crosshair and one tooltip listing all series at that date. On touch, tap-and-drag. Keyboard: arrow keys move the crosshair when the chart has focus.
- Every chart has a "Show as table" alternative and a one-sentence text summary for screen readers.
- Library: decided in Phase 3 (OPEN-QUESTIONS.md). It needs SVG output, keyboard access and custom tooltips.

## 7. Accessibility

- Target **WCAG 2.2 AA**:
  - text contrast ≥ 4.5:1 (1.4.3);
  - non-text contrast ≥ 3:1 for UI and meaningful graphics (1.4.11);
  - colour never the only signal (1.4.1);
  - targets ≥ 24×24 CSS px (2.5.8) ([WCAG 2.2](https://www.w3.org/TR/WCAG22/)).
  - Our own target for primary controls: 44 px.
- Fully keyboard-operable, with a visible focus ring (`--accent`, 2 px) and a skip link.
- `prefers-reduced-motion`: no animated chart transitions.
- Forms have programmatic labels, and errors are announced via `aria-live`.
- Automated axe checks in CI, plus a manual screen-reader pass (VoiceOver and NVDA) on the three main flows before launch.
- Reading level: aim for plain English at about school-leaver level. No jargon without the glossary tooltip below.

## 8. Plain-language copy (glossary)

Used in tooltips, the assumptions panel and "How this works". The AI explainer is given the same definitions.

| Term | Copy |
|---|---|
| Round-up | The spare change from a purchase: the amount needed to reach the next whole dollar. A $4.37 coffee has a 63¢ round-up. A $4.00 purchase has none. |
| Round-ups added | The total spare change set aside over the period. This is your own money going in, not growth. |
| Value at end | What the fund shares and any cash waiting to be invested would have been worth on the last date, at that day's closing price. |
| Difference | Value at end minus round-ups added. It can be negative. |
| ETF | Exchange-traded fund: a basket of many investments that trades like a single share. |
| Broad-market fund | A fund that holds a large slice of the whole stock market, rather than a few companies. |
| Dividend-focused fund | A fund that picks companies that pay out a share of their profits as cash dividends. |
| Dividend | Cash a fund pays to its shareholders from what its holdings earned, usually every three months here. |
| Reinvest dividends | Using dividend cash to buy more of the same fund on the day it is paid. |
| Ex-dividend date | The cut-off: you only get a dividend if you owned shares before this date. |
| Pay date | The day the dividend cash actually arrives. |
| Closing price | The official price of one share at the end of a trading day. We use it for every simulated purchase. |
| Next trading day | The first day the market is open after your purchase. Weekends and market holidays are skipped. |
| Weekly / monthly / every $5 | Instead of investing each round-up separately, saving them up and investing them together. |
| Fractional share | Part of a share. It lets small amounts like 63¢ be invested fully. |
| Expense ratio | The fund's yearly running cost, as a percentage of what you hold. It is taken out inside the fund, so it is **already reflected in the price**. We don't subtract it again. |
| Share split | When a fund changes how many shares exist, e.g. turning each share into three cheaper ones. Your total value doesn't change. |
| Hypothetical | Calculated "what if", not something that happened to real money. |
| Historical / past performance | What happened before. It doesn't tell you what will happen next. |
| Hindsight bias | We picked these funds knowing they are popular today, which makes the past look more predictable than it was. |
| Data as of | The most recent market day included in these numbers. |
| Uninvested cash | Round-ups waiting for their investment day. They count at face value and earn nothing here. |

## 10. Stage 6 redesign: direction and spec (2026-10-15)

**Goal:** modern, sleek, friendly and colourful, still calm and trustworthy, with every disclaimer visible. WCAG 2.2 AA throughout.

### Palette (hex values are in `web/app/tokens.json`; `node web/tools/contrast.mjs` prints every ratio, and `web/tests/contrast.test.ts` fails the build if any pair drops below its minimum or if gain and loss become confusable)

**Revised 2026-10-16 (owner request): green and red.** The first version of this spec used indigo and teal. Rules for the new scheme:
- **Green** is the brand accent: primary buttons, links, selected states, the "value" line, the strip's "shares" part. **Red** means a made-up loss, an error, or a negative figure ("lowest point below money put in", a negative "growth on round-ups"). **Amber** is only for neutral notes (the disclaimer). **Blue** is strategy B and the focus ring, so no red/green pair is ever needed to tell two series apart. Backgrounds stay calm: soft off-white in light mode, dark navy in dark mode.
- **Colour never carries meaning alone** (WCAG 2.2 SC 1.4.1, [Understanding Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)): every gain has a plus sign and an up arrow, every loss a minus sign and a down arrow (the `Delta` component; the arrow is decoration, the sign is what a screen reader reads). The A-versus-B difference shows its sign only, with no arrow and no colour (an arrow beside "+$2.65" reads as "better"); the round-ups line is dashed and the value line solid; chips and strip legends carry text.
- **Not advice, not a forecast:** red and green only describe a result in this made-up market. The difference between two strategies (A vs B, "B minus A", the difference line) is deliberately **neutral** (slate, with an arrow for direction): red or green there would read as "better" or "worse". There is no buy/sell colouring anywhere.
- **Green is a brand and series colour, not a verdict.** The value line, the strip's "shares" part and the scenario sparklines are green in every result, including a made-up loss and the "Crash and recovery" and "High volatility" scenarios; whether a result is a gain or a loss is said only by the signed figure with its arrow and its red or green. (An independent review pointed out that a green line ending below the dashed line can read as "good"; I kept the single series colour for consistency and say so here.)
- **Lightness as well as hue:** the gain and loss colours also differ in lightness (light theme: figures #16A34A against #B42318, L* 19 apart; dark theme: #7AE8A8 against #FF5C5C, 23 apart). Small text has to be dark enough for 4.5:1, which limits how far apart the light theme's two small-text colours can be (L* 7), so the sign and arrow matter most there.

| Role | Light | Dark |
|---|---|---|
| Page / card | `#F5F7FA` / `#FFFFFF` | `#0B1220` / `#131C2F` |
| Ink / secondary ink | `#0F1B33` / `#475066` | `#E8EDF7` / `#A9B4CB` |
| Primary (green): buttons, links, selected | `#15803D` | `#7AE8A8` |
| Green tint / slate tint | `#E4F5EA` / `#EAEFF7` | `#10291F` / `#19243D` |
| Gain: large figures and marks / small text | `#16A34A` / `#15803D` | `#7AE8A8` / `#7AE8A8` |
| Loss (red): negative figures, errors | `#B42318` | `#FF5C5C` |
| Strategy B (blue) | `#2563EB` | `#8DB4FF` |
| Focus ring (blue) | `#1D4ED8` | `#93C5FD` |
| Amber (neutral notes) | `#FFF3D1` / `#B45309` / `#3D2A00` | `#2B2208` / `#D9A441` / `#FBE7B4` |
| Hero gradient | `#0B1F4B` / `#0F6B3F` | `#0B1F4B` / `#0F6B3F` |

### Measured contrast (WCAG 2.2 AA: text 4.5:1; large text, user-interface components and chart lines 3:1; SC [1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) and [1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html))
All pairs pass in both themes; the test fails the build otherwise.

| Pair (foreground on background) | Needs | Light | Dark |
|---|---|---|---|
| body text on page (`ink` on `bg`) | 4.5:1 | 15.97 | 15.95 |
| body text on card (`ink` on `surface`) | 4.5:1 | 17.14 | 14.49 |
| secondary text on card (`ink2` on `surface`) | 4.5:1 | 8.05 | 8.16 |
| secondary text on page (`ink2` on `bg`) | 4.5:1 | 7.50 | 8.99 |
| text on green tint (`ink` on `greenTint`) | 4.5:1 | 15.14 | 13.16 |
| text on slate tint (`ink` on `slateTint`) | 4.5:1 | 14.85 | 13.14 |
| secondary on green tint (`ink2` on `greenTint`) | 4.5:1 | 7.11 | 7.42 |
| link on card (`link` on `surface`) | 4.5:1 | 6.61 | 11.29 |
| link on page (`link` on `bg`) | 4.5:1 | 6.16 | 12.42 |
| primary button text (`onPrimary` on `primary`) | 4.5:1 | 5.02 | 11.21 |
| accent button text (`onAccent` on `accent`) | 4.5:1 | 5.02 | 11.21 |
| hero heading on gradient start (`onHero` on `heroFrom`) | 4.5:1 | 16.01 | 16.01 |
| hero heading on gradient end (`onHero` on `heroTo`) | 4.5:1 | 6.57 | 6.57 |
| hero text 2 on gradient end (`onHero2` on `heroTo`) | 4.5:1 | 6.14 | 6.14 |
| amber note text (`amberInk` on `amberBg`) | 4.5:1 | 12.42 | 12.88 |
| amber note border (`amberLine` on `amberBg`) | 3:1 | 4.54 | 6.99 |
| error text (`danger` on `dangerBg`) | 4.5:1 | 5.75 | 7.10 |
| control border on card (`control` on `surface`) | 3:1 | 4.24 | 4.88 |
| control border on page (`control` on `bg`) | 3:1 | 3.95 | 5.37 |
| focus ring on card (`focus` on `surface`) | 3:1 | 6.70 | 9.43 |
| focus ring on page (`focus` on `bg`) | 3:1 | 6.24 | 10.38 |
| value line (series A) on card (`seriesA` on `surface`) | 3:1 | 5.02 | 11.29 |
| strategy B line on card (`seriesB` on `surface`) | 3:1 | 5.17 | 8.18 |
| round-ups added line on card (`added` on `surface`) | 3:1 | 8.05 | 8.16 |
| text on slate tint (chips, hover) (`ink` on `slateTint`) | 4.5:1 | 14.85 | 13.14 |
| link on slate tint (`link` on `slateTint`) | 4.5:1 | 5.73 | 10.24 |
| gain text on card (`gainText` on `surface`) | 4.5:1 | 5.02 | 11.29 |
| gain text on page (`gainText` on `bg`) | 4.5:1 | 4.67 | 12.42 |
| gain text on gain tint (`gainText` on `gainBg`) | 4.5:1 | 4.64 | 10.25 |
| loss text on card (`loss` on `surface`) | 4.5:1 | 6.57 | 5.62 |
| loss text on page (`loss` on `bg`) | 4.5:1 | 6.13 | 6.19 |
| loss text on loss tint (`loss` on `lossBg`) | 4.5:1 | 5.75 | 5.35 |
| gain mark (large figure, arrow, strip) on card (`gain` on `surface`) | 3:1 | 3.30 | 11.29 |
| loss mark (large figure, arrow) on card (`loss` on `surface`) | 3:1 | 6.57 | 5.62 |
| primary on card (selected border, radio) (`primary` on `surface`) | 3:1 | 5.02 | 11.29 |
| strategy B text/line on page (`seriesB` on `bg`) | 3:1 | 4.82 | 9.01 |

### Colour-blindness check
- **Method:** every pixel of the screenshots goes through the matrices of Machado, Oliveira and Fernandes (2009), *A Physiologically-based Model for Simulation of Color Vision Deficiency*, IEEE TVCG 15(6), at severity 1.0 (full dichromacy) for protanopia, deuteranopia and tritanopia, applied in linear RGB ([matrices](https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html); that page lists the matrices, and the linear-RGB step is the paper's model, which the page does not spell out). Code: `web/tools/cvd.mjs` (matrices and ΔE) and `web/e2e/cvd-shots.spec.ts` (screenshots). Chrome's built-in vision-deficiency emulation was not used (its documentation page could not be read here). Colour difference is CIE76 ΔE in CIELAB; as a rule of thumb ΔE above about 10 to 20 is a clear difference.
- **Images:** `web/screenshots/redesign/cvd/<screen>-<light|dark>-<original|protanopia|deuteranopia|tritanopia>.jpg` for setup, results with a gain, results with a loss, and compare (32 images).
- **Numbers (first colour against second colour):**

| Gain vs loss | Theme | Colours | L* difference | ΔE protanopia | ΔE deuteranopia | ΔE tritanopia |
|---|---|---|---|---|---|---|
| small text | light | #15803D / #B42318 | 7 | 18 | 23 | 108 |
| figures and marks | light | #16A34A / #B42318 | 19 | 33 | 20 | 115 |
| strategy A vs B lines | light | #15803D / #2563EB | 1 | 106 | 102 | 23 |
| small text | dark | #7AE8A8 / #FF5C5C | 23 | 35 | 27 | 122 |
| figures and marks | dark | #7AE8A8 / #FF5C5C | 23 | 35 | 27 | 122 |
| strategy A vs B lines | dark | #7AE8A8 / #8DB4FF | 11 | 67 | 62 | 21 |

- **Result:** under tritanopia (blue-yellow) green and red stay far apart (ΔE above 100). Under protanopia and deuteranopia they are *distinguishable* (ΔE 18 to 35) but not strongly so: in the deuteranopia images the loss figure and the green accent both turn olive/brown. That is expected for this pair, and it is why the sign, the arrow and the words carry the meaning. On the screens I could tell every gain from every loss by sign and arrow; by colour alone only with effort. Strategy A (green) and B (blue) stay apart under protanopia and deuteranopia (ΔE above 60) and, less strongly, under tritanopia (ΔE 21 to 23). **Not verified:** a person with colour-vision deficiency has not looked at the screens.

### Type
One self-hosted sans, **Manrope** (variable, loaded with `next/font/google`: downloaded at build time and served from our own origin, so no request to a font server at run time), tabular figures for every number. Scale: hero heading clamp(32 to 52 px)/1.1/800; page title 32/1.15/800; section 24/1.25/700; card title 18/1.3/700; body 16/1.55/500; small 14/1.5; axis and captions 12; hero figure clamp(40 to 64 px)/1/800; stat figure 28/1.1/800. Spacing on a 4 px grid (4, 8, 12, 16, 24, 32, 48, 64). Radii: controls 12, cards 20, hero 28, chips 999. Soft shadows in light mode, 1 px borders in dark.

### Components
Header (logo mark, nav, theme toggle: system by default, explicit override remembered) · hero with one call to action · sticky **progress rail** for the four setup steps (done / current / to do; one page, not a wizard, so every choice stays visible and keyboard order stays simple) · choice cards (radio cards with icons) · **scenario cards** with a coloured chip and a **sparkline of the model's own shape** (computed by the scenario generator, passed through the API, drawn as an SVG that screen readers skip) · large aligned inputs (equal heights, baseline-aligned labels) · weekly-purchases slider with its explanation beside it · tucked-away "adjust" disclosure · results hero figure with a **digit-roll count-up** (CSS only, no arithmetic on money, off under reduced motion) · stat cards with icons · **composition strip** · area chart · compare strategy cards with a "difference" summary · saved-scenario cards · skeleton loaders · friendly empty and error states · amber note for disclaimers · assumptions panel · footer. One icon set: 24 px stroke icons drawn for this project, inline SVG, `aria-hidden`, never the only carrier of meaning.

### Chart style
Area chart with a soft gradient fill under the **value** line (green), a dashed **round-ups added** line (slate), one axis starting at $0, recessive grid; the chart draws in once, the first time it is seen (see Motion), and not otherwise. Compare: two small multiples on a shared scale, A green and B blue, each labelled A or B so colour is never the only cue. A table and a text summary stay for every chart.

### Where I changed your direction, and why
1. **"Colour-coded strip splitting contributions, growth, dividends and cash waiting"** becomes a strip showing **what the end value is made of**: shares, round-ups waiting, dividends kept as cash (the parts always add up to the end value). Growth can be negative, which a split cannot show honestly, and the widths must come from the engine, not the browser. The shares are computed in the engine (rule R-13.4, with golden cases and an independent cross-check).
2. **Guided stepper** is one page with a sticky progress rail rather than a hide-and-reveal wizard: fewer clicks, nothing hidden, simpler keyboard and screen-reader use.
3. **Count-up** rolls the digits of the engine's own figure (CSS) instead of interpolating numbers, because the browser must never calculate a money figure.
4. **Sparklines** are drawn from the scenario model itself, not hand-drawn lookalikes, so they cannot misrepresent a scenario.
5. **Amber** stays for neutral notes only (the disclaimer); errors and negative figures are red (see the revised palette above).

### As built (2026-10-15)
- Screens, states and modes: 21 screens and states in light, dark and mobile are in `web/screenshots/redesign/after/` (JPEG, with the pre-redesign set in `before/` and accessibility-tree text in `aria/`). `web/e2e/redesign-shots.spec.ts` regenerates them; `web/tools/compress-shots.sh` makes the JPEGs.
- The spec above was built as written. Differences: scenario sparklines share one log scale across all eight scenario series (per-scenario scaling made "sideways" look like a crash); the progress rail follows the scroll position (an intersection observer picked the wrong step); the digit roll takes about a second and is off under reduced motion; the hero figure is drawn with digit windows whose real text stays in the page for screen readers and copying.
- Open visual notes from my own look at the screenshots: on the results page the "Show the chart as a table" link sits close to the line below it; the composition strip shows the waiting round-ups as a very thin sliver when they are tiny (correct, but easy to miss, and the legend carries the number).

### Changes after the owner's review (2026-10-15)
- **Sparklines:** 96 px tall (was 36) with a dashed line at the starting level. **Scaling rule:** every card uses the same vertical scale, so one height means the same relative change on every card. The engine computes it (R: `shape`): each series is one share's value divided by its own first value, on a log scale, and the lowest and highest values across all eight published series map to 0 and 100. I did not zoom each card to its own range: that made a gentle drift look like a crash (the first version did). The dashed line shows where each series started. The taller box makes the shapes differ clearly: a steady climb, a dip and recovery, a flat wander near the start, big swings. **History:** in scenario-model-1 the broad-market "Sideways" series fell to about 0.31 of its start, which contradicted its card text. **Resolved 2026-10-16 (OQ-15):** the model now keeps Sideways in a stated band (SCENARIO-MODEL.md), and its sparkline is flat on the shared scale.
- **Phone header:** a single bar (logo, theme button, Menu button, 44 px targets). The Menu button is a disclosure (`aria-expanded`, `aria-controls`), not `role="menu"`; Escape closes it and returns focus to the button; picking a link or changing page closes it; without JavaScript the links stay visible.
- **Compare:** the "Both use the same round-ups..." note now sits inside the difference box, directly under the difference sentence (the wording is unchanged and appears once). The two charts reserve the same title height so their plots line up side by side (tested: same top and height).
- **Slider:** "1" and "60" are shown under its ends (hidden from screen readers, which already hear the slider's own limits).
- **Screenshots:** the accessibility run's own PNGs are written to `web/screenshots/a11y/` (git-ignored) instead of overwriting tracked files on every run; the committed set is `redesign/after/`.

### Motion (2026-10-16, owner request)
CSS first, no animation library (the JavaScript added is about 3 KB: `web/lib/inpage.ts`, `web/lib/reveal.ts`, `web/components/MotionInit.tsx`). Sources read: MDN on [`prefers-reduced-motion`](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion) (honour the "reduce" request by removing or replacing motion), [`scrollend`](https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollend_event) and [`focus({ preventScroll })`](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/focus).
- **Smooth in-page links.** A click on the progress rail, "Start a simulation" or any `#section` link scrolls smoothly (the sticky rail is allowed for by `scroll-margin-top`), puts the section in the address bar, highlights the chosen step at once (and keeps it while the page scrolls), and, when the scroll has ended (`scrollend`, with a 1.2 s timer as a fallback for browsers without it), moves keyboard focus to the section's heading without scrolling again. The heading gets `tabindex="-1"`: focusable by script, not an extra Tab stop. The "Skip to main content" link, modified clicks and unknown ids keep the browser's own behaviour. Focus moves only because the person activated that link.
- **Entrance.** Cards, stat tiles, the strip, compare and saved cards, and sections fade and rise 16 px as they scroll into view, staggered by 70 ms (at most five steps). Things already on screen when the page loads are left alone (no flash); the hero's text rises in with CSS from the first paint; things added later that are on screen animate at once. Once per element, never again.
- **Chart.** Reveals left to right once, the first time it is seen (1.2 s), and leaves no clip behind (so the focus ring is not cut).
- **Other.** The existing digit roll on the big number; hover lift (`translate`) and press shrink (`scale`) on cards and buttons; the rail's dots and borders ease between states; light and dark ease into each other for 0.3 s after the toggle is pressed.
- **Reduced motion.** `<html data-motion="on">` is set before the first paint unless the person prefers reduced motion, and every rule also sits under `@media (prefers-reduced-motion: no-preference)`, so changing the setting later is respected. With "reduce": links jump instantly and still move focus, nothing is marked for animation, nothing is hidden or moved, no animation or transition runs, the digit roll is a plain number. A final blanket rule switches off any animation and transition.
- **Never hides content.** Pending elements are only faded and lowered (opacity and transform); they stay in the page, in the accessibility tree and in the tab order, and a pending element that holds focus is shown at once (`:focus-within`). A print rule shows every pending element (tested in the stylesheet; I did not print a page). Find-in-page still finds text in a faded-out card, but it will scroll to it first, which reveals it.
- **Tests.** Every other end-to-end, geometry, axe and screenshot test runs with reduced motion (set in `playwright.config.ts`), so they see the page at rest. `web/e2e/motion.spec.ts` runs the motion cases explicitly: smooth scroll (several in-between positions), the step highlight at once, landing below the sticky rail, focus on the heading, the skip link unchanged, pending then in, keyboard focus reveals, nothing clipped or overlapping after the animations finish (checked while scrolling the whole page), the chart draws once and leaves no clip, the theme transition class, hover lift, and reduced motion (instant jump, no marked elements, no running animation, all cards opaque). Unit tests: `tests/inpage.test.ts`, `tests/reveal.test.ts`.
- **Size and speed** (local production build, first load of the setup page): 637,728 B before, 646,377 B after (+8.6 KB: script +3.7 KB, stylesheet +2.4 KB, the rest is markup); to the results page 1,080,975 B before, 1,090,934 B after. Time to network idle measured back to back on the same machine: 845 and 867 ms before (a clean checkout of the previous commit), 847 to 861 ms after, so no measurable change.

### Changes after the independent review of colours and motion (2026-10-16)
- **Focus handling** (`lib/inpage.ts`): a newer click cancels an older pending focus move; typing, wheel or touch before the scroll ends cancels it; focus is only moved if it is still on the link the person used (or on nothing); a section already in place gets focus at once instead of after the 1.2 s fallback. Tested in `tests/inpage.test.ts`.
- **Reveal safety** (`lib/reveal.ts`): at the very bottom of the page everything still waiting is shown, because nothing can intersect the shrunk viewport there. A print rule shows everything.
- **No global smooth scrolling:** `html { scroll-behavior: smooth }` is removed. The scripts pass the behaviour explicitly, so the skip link and Back/Forward jump natively, and Next's own scroll on page change is not slowed.
- **Hover lift** only on cards that can be opened (saved scenarios), not on read-only tiles.
- **Not changed, on purpose:** the green series colour in a loss result (see above); small differences in the light-theme small-text gain/loss colours (L* 7), which the sign and arrow cover.
