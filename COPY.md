# RoundUp: exact on-screen wording (stage 5)

This is the single source for user-facing text in the mocks and the web app. **Bold** marks emphasis as it appears on screen. `{…}` is filled from API strings, formatted only (no arithmetic). Any change here needs owner approval.

## Always visible (every page)

- **Label strip, under the top bar:** "Synthetic scenario. Not a real fund, not real prices, and not a forecast."
- **Footer:** "RoundUp is an educational demo. No money moves and nothing here is advice or a forecast." · Privacy · How this works

## Disclaimer box (results and compare, above the numbers)

> **Hypothetical simulation on a synthetic market.** These results show how sample round-ups behave in a made-up market scenario. No money was invested, the prices are not real, and this is not a forecast. It is not investment, tax or financial advice.

(For uploaded files the word "sample" is dropped: "…how round-ups from your file behave…")

## Key points (always visible; replaces the long open assumptions panel)

Heading: **Key points**
- **Made-up prices.** The scenario is invented. It is not a real fund or a real market.
- **Not a forecast.** It says nothing about what any market will do.
- **No fees included.** Real round-up apps may charge fees that matter a lot for small balances.
- **Not advice.** Nothing here suggests what you should do with your money.

Below it, collapsed by default on every screen size:
- `<details>` **All assumptions ({n})**. Each item shows a title and one sentence, with no rule codes. The API's assumptions are listed in order, ending with the API disclaimer.
  - Inside it, a nested `<details>` **Rule references** lists "{title}: {rule id}" (e.g. "Round-ups: R-2.1"), for people who want to check the published finance rules.

## Results screen

- **H1:** "Your sample round-ups in a made-up market" (uploaded file: "Your round-ups in a made-up market")
- **Headline:** "In this made-up scenario, **{contributed}** of sample round-ups ends at **{ending_value}** on {as_of}: **{|gain|}** {more|less} than was put in."
- **Stat tiles** (each label is a button that shows the definition):

| Label | Value | Note under the value | Definition (shown when the label is pressed) |
|---|---|---|---|
| Round-ups added | {contributed} | from {n} sample purchases | The spare change set aside from the purchases. This is money going in, not growth. |
| Value at end | {ending_value} | on {as_of} | What the shares, cash waiting to be invested and dividends kept as cash would be worth on the last day. |
| Dividends (simulated) | {dividends_earned} | {dividend_buys} payments reinvested | Cash the made-up fund paid out from what its holdings earned. |
| **Growth on round-ups** | {±gain} | compared with the round-ups added (no percentage: owner decision 2026-10-13) | How far the value at the end is above, or below, the round-ups added. It can be negative. |

- **Lowest point** (under the chart, from `deepest_dip`):
  - With a dip: "**Lowest point compared with money put in:** on {date} the value was {value}, which was {below_by} below the {added} of round-ups added by then."
  - Without: "**Lowest point compared with money put in:** the value never fell below the round-ups added in this scenario."
- **Not yet invested** (under the chart): "On the last day, {roundups_waiting} of round-ups was waiting to be invested and {dividends_as_cash} of dividends was kept as cash."
- **How often money was invested:** "Money was invested {roundup_buys} times from round-ups and {dividend_buys} times from dividends."
- **Chart caption:** the engine's `series_rule`, then "Scenario dates follow a real calendar, but the prices are made up."
- **Chart summary** (for screen readers, and shown above the table toggle): "From {start} to {end} the value goes from {first value} to {last value}, with ups and downs in between, while the round-ups added go from {first added} to {last added}." The lowest-point sentence follows directly under the chart, so it is not repeated inside the summary (changed in build: it appeared twice).
- **Table toggle:** "Show the chart as a table"
- **Explainer placeholder** (clearly marked):
  - Heading: "Questions about these numbers".
  - Text: "**Coming later:** an AI explainer that only describes these numbers. It will never predict or advise."
  - No buttons.
- **Actions:**
  - Signed out: "Sign in to save" and "Compare with another way of investing".
  - Signed in: "Save this scenario".
- **Technical details** (collapsed): "Scenario {id}, seed {seed}, {model_version}; engine {engine_version}; input checksum {checksum}. These let anyone reproduce the exact numbers."

## Compare screen

- **H1:** "Compare two ways of investing"
- **Intro:** "Same sample purchases, same synthetic scenario ({scenario}, {style}, {start} – {end}). Only the settings below differ. Scenario dates follow a real calendar, but the prices are made up."
- **Rows:**
  - Round-ups added
  - Value at end
  - **Growth on round-ups**
  - Dividends (simulated)
  - **Round-ups waiting to be invested**
  - **Dividends kept as cash**
  - Times invested from round-ups
  - Times invested from dividends
- **Columns:** "A", "B", "B minus A"
- **Note:** "Both use the same round-ups, so "B minus A" is the same for value at end and for growth on round-ups. Cash waiting and dividends kept as cash are part of the value at end. These differences come from this one made-up scenario and say nothing about which choice works better in general."
- **Lowest point per side:** "A, lowest point compared with money put in: …" (same sentence as on the results screen), and the same for B.

## Setup screen (unchanged from the reviewed mocks)

- "When they reach $5" carries the tag **Starting setting**.
- "All four are equally valid to explore. Comparing them is the point."
- Style descriptions: "In this model: smaller dividends, slightly higher price drift." and "In this model: larger dividends, slightly lower price drift."
- "Sample number (same number, same purchases)"

## Saved scenarios

- **Intro:** "Saved scenarios keep their results exactly as calculated. They are not backed up in this demo. Every saved result comes from a synthetic scenario: not a real fund, not real prices, and not a forecast."
- **Empty:** "Nothing saved yet" / "Run a simulation, then choose **Save** to keep it here."
- **Signed out:** "Sign in to see saved scenarios" / "You can run simulations without an account. Signing in only lets you keep them. We send a one-time sign-in link to your email; there is no password."
- **Sign-in not set up** (no Supabase configured): "Sign-in isn't set up on this copy of RoundUp, so saving is turned off. Everything else works."
- **Delete confirmation:** "Delete "{name}"? This removes the scenario and its results. It can't be undone." Buttons: "Delete" / "Keep it".

## Error messages

The API's plain-language `error.message` is shown as is. The web app adds only these:
- **Network:** "We couldn't reach the RoundUp service. Check your connection and try again."
- **Rate limit:** "Too many requests. Please wait {seconds} seconds and try again."
- **Session expired on save:** "Your sign-in has expired. Sign in again to save. Your results are still here."
- **No results yet** (results page opened directly): "No results yet" / "Run a simulation first." Button: "Set up a simulation"
- **All whole-dollar purchases:** "These purchases were all whole-dollar amounts, so there was no spare change to invest."

## Added after the stage-5 web review (approved by the owner on 2026-10-13)

Each line fixes a reviewer finding (H = high, M = medium, L = low; see TEST-STRATEGY.md §stage 5).

**Results**
- **Rows not counted** (H2; shown under the stat tiles whenever `transactions_ignored` is not "0"): "{n} row(s) add(s) no round-ups because they fall outside the chosen dates or are not purchases (money coming in, payments, transfers or fees, or pending or cancelled rows)."
- **No purchases in the window** (H2; replaces the whole-dollar sentence when `transactions_used` is "0"): "None of these rows were purchases between the chosen dates, so there was no spare change to invest."
- **No trading day** (H1; the API now refuses such dates, and this is the fallback if a result ever has no chart points): "There is no trading day between these dates, so there is nothing to show. Choose a wider date range."
- **Chart keyboard hint** (M6, under each chart): "To read values with the keyboard, select the chart, then use the arrow keys, Home, End, Page Up and Page Down."
- **Chart readout** (M6; visible, and announced when the keyboard moves): "{date}: value {value}, round-ups added {added}." (+ " Price carried from the last trading day." when `carried`)
- **Chart summary, special cases** (L7): one point: "On {date} the value is {value} and the round-ups added are {added}." Value unchanged throughout: "From {start} to {end} the value stays at {value}, while the round-ups added go from {first added} to {last added}."
- **Sign in to save** (M7; the form now opens on the results page instead of leaving it). After the link is sent: "Check your email for a sign-in link. It works once. Keep this tab open: your results stay here, and you can save them once you're signed in."
- **Technical details** (L5): "Scenario {id} ({style}), scenario seed {seed}, model {model_version}; engine {engine_version}; input checksum {checksum}. Settings: {purchases}; {start} to {end}; {strategy}; {dividends}. The same settings and purchases give exactly these numbers again." `{purchases}` is "sample number {n}, up to {k} purchases a day", "purchases from your file" or "purchases as saved".
- **Plurals** (L8): "from 1 sample purchase", "1 payment reinvested", "invested 1 time".

**Setup**
- **Sample number hint** (M3): "A whole number from 0 to 2,147,483,647." Errors: "Use a whole number from 0 to 2,147,483,647 for the sample number." / "Use 1, 2 or 3 for purchases per day." Only the wrong field is marked.
- **Check step, dates** (H2, M5): "Dates in this file run from {first} to {last}." If any row is outside the dates in step 4: "Some rows fall outside the dates in step 4, so they won't add round-ups." with the button "Use this file's dates" (kept inside the scenario's range).
- **Slash dates** (M5; shown when the file has dates like 01/06/2020): "Dates written with slashes are read as month/day/year (US style), so 01/06/2020 is January 6, 2020. If your bank writes the day first, these dates will be wrong."
- **Sign options** (M4): "Money out and money in columns" (was "Separate columns for money out and money in"; shortened in stage 6 so it fits a phone) now shows "Money out column" and "Money in column"; "A column says debit or credit" shows "Debit or credit column". Missing column (from the API): "Choose which column holds the amount." (or "debit or credit", "money out", "money in").
- **CSV problems** (L9): empty file: "The file is empty."; semicolons: "This file seems to use semicolons between columns. Save it with commas between columns and upload it again."; one column chosen twice: "Choose a different column for each field."
- **Rate limit** (L2): same message; the Run and Compare buttons stay disabled until the wait ends.

**Compare** (L11: wording that was in the app but not here)
- "B minus A" cell for round-ups added: "same for both"; for cash waiting and dividends kept as cash: "see A and B".
- Empty state: "Run a simulation first; the comparison uses the same purchases and scenario."

**Saved** (L10)
- After a delete: "Deleted “{name}”." (announced; focus moves to the page heading).

## Upload step, after the owner's testing on the preview (2026-10-13; applied, for the owner's sign-off)

- **Sign-convention box:** label "How are amounts signed?". It starts on the prompt "**Choose how amounts are signed**", not on an option. The four options are "Purchases are positive numbers", "Purchases are negative numbers", "Money out and money in columns" (was "Separate columns for money out and money in"; shortened so it fits a phone) and "A column says debit or credit".
- **Help beside the box, before any choice:** "Banks write purchases in different ways. Look at one purchase in your file. If it is a positive number (like 6.16), choose “Purchases are positive numbers”. If it has a minus sign (like -6.16), choose “Purchases are negative numbers”. If money out and money in are in two columns, or a column says debit or credit, choose the matching option."
- **Help after a choice** (one sentence each):
  - positive: "Purchases are positive numbers, like 6.16. Refunds and other money coming in are negative, like -12.50, and never add round-ups."
  - negative: "Purchases are negative numbers, like -6.16. Money coming in is positive, like 12.50, and never adds round-ups."
  - two columns: "Purchases are in the money out column. Money coming in is in the money in column and never adds round-ups."
  - debit or credit: "A column says debit or credit for each row. Debits are purchases. Credits are money coming in and never add round-ups."
- **Chosen for you (only when the column names make it plain, R-1.3):** "We chose this because your file has columns named “{out}” and “{in}”. Change it if that is wrong." or "We chose this because your file has a column named “{type}” next to the amount. Change it if that is wrong." A single signed Amount column is never guessed.
- **Error (nothing is sent to the API):** "Choose how amounts are signed in this file, in the box named “How are amounts signed?”. Your options are: “Purchases are positive numbers”, “Purchases are negative numbers”, “Money out and money in columns”, or “A column says debit or credit”." The box is marked invalid, gets focus, and its help adds "Choose one of the four options."
- **New picker:** "Status column (optional)", found automatically when a column is named Status. Without it, pending and cancelled rows were counted as purchases.
- **Check step, new sentences:** "Money coming in (refunds, deposits): {n}. These never add round-ups." · "Pending or cancelled rows: {n}. These are left out." · "Purchases of an exact dollar amount: {n}. These add $0.00, because there is no spare change."

## Applied 2026-10-14 (approved by the owner): clearer "Sample number" wording

Today: label "Sample number (same number, same purchases)", hint "A whole number from 0 to 2,147,483,647."; "Purchases per day, at most", hint "1, 2 or 3."

Proposal (plain language: the number picks which made-up purchases are used; the same number always gives the same results):
- Section line above the two fields: "RoundUp makes up a list of everyday purchases for you. The number below picks which list."
- Label: "**Made-up purchase list number**"
- Hint: "Pick any whole number from 0 to 2,147,483,647. The same number always gives the same purchases and the same results. A different number gives a different list."
- Label: "**Most purchases in one day**"; hint: "Choose 1, 2 or 3. Each day gets anywhere from none up to this many made-up purchases."
- Error: "Use a whole number from 0 to 2,147,483,647 for the made-up purchase list number." (the "Use 1, 2 or 3…" error keeps its wording)
- Technical details: "sample number 42, up to 2 purchases a day" becomes "purchase list number 42, up to 2 purchases a day".

The first label, "Made-up purchase list number", was approved; the shorter alternative was not used. The change is limited to the setup form, its errors and the technical-details line.

## Check step, after the independent review of the upload flow (2026-10-14; applied, for the owner's sign-off)

- "Purchases that will add round-ups: {n}." (always shown, so a wrong sign choice shows up as a surprising number)
- **No purchases:** "None of these rows would add round-ups. If you expected some, check the box named “How are amounts signed?”: with the wrong choice, purchases can look like money coming in."
- **Rows with extra values:** "{n} rows have more values than the header has columns. A comma inside a number (like 6,16) splits it in two, so the amount can be read wrongly. Put such amounts in quotes, or use a dot (6.16)."
- **Empty:** "This file has no rows below the header."
- **Dates:** "Dates must look like 2024-01-31, or like 01/31/2024 (month first). A time after the date is not accepted." (shown when any date cannot be read)
- **Tabs:** "This file seems to use tabs between columns. Save it as a CSV with commas between columns and upload it again."
- Blank lines before the header are skipped. Choosing an option in the sign box clears its error.

## Statuses (R-1.4a, owner decision OQ-12, applied 2026-10-14)
- **Check step, when a Status column holds words other than posted, settled, cleared, completed, pending or cancelled:** "{n} rows have a status we don’t recognise. We count only the statuses posted, settled, cleared and completed as purchases, so these rows are left out for now." (singular: "1 row has a status we don’t recognise. …"), with a box "**Count these rows as purchases too**" (off by default). When ticked: "{n} rows will be counted as purchases." Status words from the file are never shown.
- **Dates with a time (OQ-13):** still rejected. The message is the one above: "Dates must look like 2024-01-31, or like 01/31/2024 (month first). A time after the date is not accepted."

## Typical spending (R-1.9, owner decision 2026-10-15; replaces "Generate sample spending", the purchase list number and "Most purchases in one day")
- **Source choice:** "**Typical spending**" · "An estimate from averages: you tell us how many purchases you make in a typical week." (the other choice stays "Upload a CSV").
- **Always shown with it:** "This is an estimate based on averages. Real spending varies."
- **Question:** "How many purchases do you make in a typical week?" with a slider and a number box. Hint: "A whole number from 1 to 60. The purchases are spread evenly across the week, weekends included." Error: "Enter a whole number of purchases from 1 to 60."
- **Tucked-away box** (closed until opened; opened automatically on an error): "**Adjust the average round-up**" · "A round-up is the spare change up to the next dollar. Across everyday prices the average spare change is about 50 cents, so $0.50 is the starting setting. Choose a higher average if your purchases usually end just under a whole dollar, or a lower one if they usually end just over." Field: "Average round-up per purchase", hint "From $0.01 to $0.99, written like 0.50." Error: "Enter an average round-up from $0.01 to $0.99, written like 0.50."
- **Results:** under the settings chips, "Estimate: {n} purchases a week, each with a round-up of {$avg}. Real spending varies." Technical details: "typical spending, {n} purchases a week, average round-up {$avg}".
- **No live "estimated round-ups" preview** while the slider moves: it would need arithmetic in the browser (not allowed) or an API call on every move (the rate limit). The exact figure appears on the results page.

## Redesign (2026-10-15; every disclaimer above is unchanged and stays visible)
- **Hero (setup page):** small label "An educational demo" · heading "See how spare change behaves in a made-up market" · "Say how many purchases you make in a typical week, pick a made-up market, and watch the round-ups add up. Everything here is an estimate on made-up prices: no real money, no real funds, no advice." · one button "Start a simulation" and a quieter link "How this works".
- **Progress rail:** "Your purchases", "Market scenario", "How round-ups are invested", "Dates" (read out as "Step n of 4: ...").
- **Scenario chips** (next to each made-up market, beside its sparkline, which screen readers skip): steady growth "Gradual rise", crash and recovery "Dip and back", sideways "Wanders about", high volatility "Big swings". They describe the shape of the invented prices, never what a real market will do.
- **Results hero:** "Value at the end, {date}" with the engine's figure; the sentence below it ("In this made-up scenario, ...") is unchanged.
- **Stat cards:** "Round-ups added", "Value at end", "Dividends (simulated)", "Growth on round-ups" (dollar figure only, OQ-9), each with an icon that is hidden from screen readers.
- **Composition strip:** heading "What the end value is made of"; legend "Invested in shares", "Round-ups waiting to be invested", "Dividends kept as cash", each with its dollar figure.
- **Compare:** two cards, A and B, and one sentence: "In this one made-up scenario, B ends {amount} higher/lower than A on the last day." or "...A and B end at the same value on the last day."
- **Theme button:** names the current choice (system, light, dark) and what pressing it does.
- **Loading, empty and error states:** skeleton cards while scenarios load (announced as a status message, not by the skeletons); "Nothing saved yet" with a "Start a simulation" link; errors say what happened and what to do ("We couldn't reach the RoundUp service. Check your connection and try again.").
