# Ambiguities and interpretation choices (crosscheck.py)

**Status after coordinator review:**
- AMB-1, AMB-4 and AMB-7 were resolved, and FORMAT.md and FINANCE-RULES.md were updated. The resolutions are recorded under each entry.
- AMB-2, 3, 5, 6, 9, 10, 11, 12, 13, 15 and 16 were confirmed as intended.

Each entry lists the rule, the competing readings, and the reading implemented. Entries marked **[output-affecting]** can change fixture results.

## AMB-1 — R-6.3(b) vs FORMAT.md: scope of GAP_ON_EVENT [output-affecting]
- Reading A (FINANCE-RULES R-6.3(b), and §16 "fails the run wherever it is in the input"): a split or dividend ex-date with no close fails the run **anywhere in the market input**.
- Reading B (FORMAT.md): "Gap rules (R-6.3(a)(b)) apply only inside the window."
- **RESOLVED:** the check covers the whole input (reading A). However, an event whose ex-date is **after the data end** (the last close in the input) is "no data yet" (R-6.5): it is ignored entirely, with no check of any kind and no effect. An event dated exactly on the data end is still checked. The `GAP_ON_EVENT_SCOPE` switch has been removed.
- The original sub-question (whether an ex-date after the last close should fail under reading A) is settled by the resolution above.

## AMB-2 — R-0.1: invalid transaction amount [output-affecting]
- Reading A: the whole import or run is rejected. R-0.1 says "rejected at import".
- Reading B: only that row is rejected.
- **Chosen: B.** The row counts as `transactions_ignored`, because FORMAT.md has no error code for a bad amount. The accepted grammar is `digits[.d|.dd]`, plus the form `.dd`. A sign (`-1.00`), whitespace, or 3+ decimals (including `1.500`) makes the row invalid.

## AMB-3 — R-1.4: matching the phrase `cash app`
- Reading A: plain substring of the normalized description. With this reading, `cash apple` matches.
- Reading B: the two consecutive whole words `cash` `app`.
- **Chosen: B.** This is consistent with the whole-word rule. Under it, `cash-app` and `CASH APP*BOB` match, while `cashapp` and `cash apps` do not.
- Related point: whole-word matching is literal, so `payments`, `fees` and `transfers` do **not** match. Words are runs of Unicode alphanumerics (`str.isalnum`). The type field (R-1.4(a)) is compared by exact equality after R-4.5 normalization, so a type of `loan payment` is **not** a non-purchase by type.

## AMB-4 — Transaction counts on an error run
- FORMAT.md says that on error `summary`, `buys` and `series` are null. It is silent on `transactions_used` and `transactions_ignored`.
- **RESOLVED:** on error runs, both counts are `null`, like `summary`, `buys` and `series`.

## AMB-5 — R-7.5: what is "P = the close of the last session before X" [output-affecting]
- Reading A: P is the last **session**, meaning the last day that has a close, so data-gap days are skipped.
- Reading B: P is the last **calendar-open day** before X. If that day is a data gap, there is "no close at P" and the series is rejected.
- **Chosen: A.** "Session" is defined in §5 as a calendar-open day with a close, so under A the "no close at P" clause only fires when no earlier close exists at all. The self-test "raw split ok, P skips gap" passes under A and would fail under B.

## AMB-6 — R-6.3(a): a gap run that straddles the window start or end [output-affecting]
- Reading A: count only the missing days inside [start, end].
- Reading B: count the whole run of consecutive missing calendar-open days if any part of it is inside the window.
- **Chosen: A.** FORMAT.md says gap rules "apply only inside the window". For example, 2 missing days before start and 2 after does not fail.

## AMB-7 — R-6.3 / R-7.5 overlap: split ex-date with no close
- Such a split fails both R-7.5 ("no close at Q") and R-6.3(b).
- **RESOLVED:** the precedence has changed, and `GAP_ON_EVENT` now comes before `SPLIT_ADJUSTED_SERIES`. Such a split therefore reports `GAP_ON_EVENT`.
- The new order is: WINDOW, CLOSE_ON_CLOSED_DAY, EVENT_NOT_CALENDAR_DAY, MISSING_PAY_DATE, EX_AFTER_PAY, GAP_ON_EVENT, SPLIT_ADJUSTED_SERIES, GAP_TOO_LONG.

## AMB-8 — R-12.1: "first close" and "last close" when some closes are invalid
- R-6.5 defines the data end as "the last close that **passed ingestion checks**". A close dated on a closed day fails ingestion, yet `WINDOW_OUTSIDE_DATA` is checked before `CLOSE_ON_CLOSED_DAY`.
- **Chosen:** the window check uses the min and max over **all** close dates as given. Any bad close then yields `CLOSE_ON_CLOSED_DAY` anyway, unless the window check fires first.

## AMB-9 — R-6.2 / R-8.5: when `delayed_by_data_gap` is set
- The literal condition is: "the first calendar-open day after C (round-ups) / on or after the pay date (dividends) is a data gap".
- **Chosen:** literal. The flag looks only at the **first** such calendar-open day.
  - A buy is not flagged if C is a gap day but C+1 has a close. For example, a monthly cut-off on a gap day 01-31, bought on 02-01, is not flagged.
  - A dividend whose pay date falls on a weekend and whose next calendar-open day has a close is not flagged.
  - The flag is only reported for buys that actually execute within the window.

## AMB-10 — R-6.4 / R-13.2: the `carried` flag when nothing is held
- Reading A: `carried` is true on every data-gap day, even with 0 shares, when the price does not affect the value.
- Reading B: only when a carried price was actually used for valuation.
- **Chosen: A.** On a gap day the carried close is looked up regardless, and the point is marked carried.

## AMB-11 — R-5.4 / R-12.1: execution sessions inside the data but after `end`
- **Chosen:** a batch or dividend buy executes only on a session in [start, end]. A cut-off that is ≤ end but whose next session is after end stays cash, as R-5.4 says.
- Weekly and monthly cut-offs that fall after `end` also stay cash, even if sessions occur before `end`. For example, January round-ups with `end` = 01-20 under the monthly strategy are never bought.

## AMB-12 — R-8.2 / R-8.3: dividends whose ex-date is before `start`, and splits outside the window
- Shares are always 0 before `start`, because only in-window transactions are used. Such dividends therefore create nothing, and such splits multiply 0.
- These events are still **validated** (whole-input checks).

## AMB-13 — R-13.1: summary when `end` is not a calendar-open day
- **Chosen:**
  - Uninvested cash includes round-ups dated after the last calendar-open day but ≤ end, for example a Saturday purchase when end is that Saturday.
  - Dividend cash with pay date ≤ end moves from receivable to cash.
  - The series has no point for `end` in that case, so the last series value can differ from `ending_value`.

## AMB-14 — R-0.3: exact rationals vs 28-digit Decimal (deliberate difference, not an ambiguity)
- This implementation uses exact `Fraction` arithmetic. The rules prescribe Decimal at 28 significant digits.
- The two can differ only when an exact value lies within about 1e-26 of a display rounding boundary, so any mismatch traced to this is a genuine knife-edge.
- A related subtlety for that engine: values that land exactly on a half-cent tie under exact arithmetic (for example dividend cash of 0.005) are rounded half-even here (to 0.00).

## AMB-15 — Normalization of `status` / `direction`
- FORMAT.md lists exact lowercase values. **Chosen:** compare after R-4.5 normalization, so `Posted` and `posted` are treated alike.
- Any status other than `posted` (`pending`, `cancelled`, unknown) is ignored (R-1.4, R-3.2). Any direction other than `debit` is ignored (R-1.8).

## AMB-16 — R-5.2 threshold: what counts toward "reaches ≥ $5.00"
- **Chosen:** the unbatched running total is accumulated per purchase date over all in-window round-ups, with no carry-over of the excess. The whole running total becomes the batch.
- Zero round-ups do not change the total. A date that has only $0 round-ups can never be a cut-off.

## AMB-17 — R-6.3(c) / R-8.5: pay date on a day that is not calendar-open (seen in G-32b and 14 R-* scenarios)
- R-6.3(c) only requires **ex-dates** to be calendar-open days, so the rules are silent on pay dates.
- Reading A: a pay date on a weekend or holiday is valid.
- Reading B: it is a data error, like an ex-date.
- **Chosen: A.** There is no error code for it.
  - The cash becomes "paid" on the pay date itself, and counts in `dividends_paid` if pay ≤ end, even when end is a Saturday (G-32b).
  - Reinvestment uses the first session on or after the pay date.
  - `delayed_by_data_gap` is set only if the first calendar-open day on or after the pay date has no close (AMB-9).

## AMB-18 — R-0.1 vs closes with more than 2 decimals (seen in G-H2: close "0.475")
- R-0.1 rejects money inputs with more than 2 decimals.
- Reading A: that applies only to transaction amounts, which are user cash flows (R-0.2).
- Reading B: it also applies to prices.
- **Chosen: A.** Prices, dividend `amount_raw` and split ratios are parsed exactly at any precision (R-0.5(b) treats them separately). The `price` field echoes the input string unchanged.

## AMB-19 — `deepest_dip`: compare on exact or displayed values [output-affecting, rare]
- Reading A: rank days by the exact (added − value).
- Reading B: rank days by the difference of the displayed, cent-rounded series values.
- **Chosen: A.** FORMAT.md says `below_by` is "exact, then rounded", and R-0.4 has one rounding point. The tie-break ("earliest wins") therefore applies only to **exact** ties.
- Two days whose `below_by` both display as 0.01 can resolve to the later day (self-test "dip exact beats display tie"). A value that is exactly below `added` by less than half a cent still counts as a dip, with `below_by` "0.00".

## AMB-20 — `deepest_dip.added`: what counts as "round-ups dated on or before that day"
- **Chosen:** every in-window round-up whose purchase date is ≤ the series day, whether invested or not.
  - This includes purchases on non-calendar days, such as a Saturday purchase, which counts on the following Monday's point.
  - Whole-dollar purchases add $0.
- `added` never includes dividends. A dividend can therefore lift the value above `added`, but cannot add to it.

## AMB-21 — FORMAT.md series `auto` mode, `series_resolution`, `series_rule`, per-point `added`
- These are described for the API's `run_scenario(s, series="auto")`.
- **Chosen:** not implemented. The cross-check covers only the default `daily` mode, whose output shape has none of these keys.
- `deepest_dip` is always judged over every daily point, which matches the "before any chart thinning" wording.

## AMB-22 — `roundups_waiting` / `dividends_as_cash` when `end` is not a calendar-open day
- Same reading as AMB-13: both parts are evaluated at `end` itself, not at the last calendar-open day.
  - Round-ups dated after the last calendar-open day but ≤ end are waiting.
  - Dividends with pay date ≤ end are cash.
- The exact parts sum to `uninvested_cash`. The displayed parts can differ from the displayed total by $0.01 (R-0.4).

## AMB-23 — R-12.1 (stage 5): "at least one close lies inside [start, end]"
- **Inclusive ends.** The bracket notation in R-12.1 and FORMAT.md reads as a closed interval, so a close on `start` or on `end` counts. A single-session window (start = end = a session) is valid. This seemed clear enough, but it is recorded because nothing says "inclusive" in words.
- **What counts as "a close".** Reading A: any entry in the input `closes`. Reading B: only a close on a calendar-open day.
  - This matters only when a close sits on a closed day inside an otherwise empty window, for example a Saturday close in a weekend-only window. Under A the window passes and the run fails with `CLOSE_ON_CLOSED_DAY`. Under B it fails with `WINDOW_OUTSIDE_DATA`, which comes first in the precedence order.
  - **Chosen: A.** The check is literal about "a close", and the result is an error under both readings, so only the code can differ.
- **Gap-only windows.** A window whose only calendar-open days have no close (data gaps) also has no close inside it. **Chosen:** `WINDOW_OUTSIDE_DATA`, as the rule text says, not `GAP_TOO_LONG` (which needs 4+ days anyway).
- The required "message naming the fund and its available range" is not part of the FORMAT.md output contract (only `error_code` is), so the cross-check does not produce it.

## AMB-24 — R-1.4a (cautious status rule): edge cases in the status text
- **Normalisation.** R-1.4a says "normalised as in R-4.5", but R-4.5 is titled as the description rule. **Chosen:** apply the same function (trim, case-fold, collapse internal whitespace), so `"ON  HOLD"` is `on hold` and `"completed "` is `completed`.
- **Empty or absent status.** At the engine boundary this is posted, so it is counted. The second sentence about imported files ("a blank cell is unrecognised" when a Status column is chosen) is an importer concern: the importer maps such a cell to `unrecognised` before the engine sees it. The cross-check implements only the engine boundary. A whitespace-only status normalises to empty and is posted (assumption: "empty" includes whitespace-only, by trimming). A JSON `null` status is treated as absent.
- **Credit with an unrecognised status.** Reading A: it is ignored as a credit (R-1.4, R-1.8). Reading B: it is ignored as an unrecognised status. **Chosen:** no distinction is made. The row is ignored once, so `transactions_ignored` is the same under both readings. Only the reason label would differ, and the cross-check emits no reasons.
- **Order of reasons.** A row that is also a non-purchase, zero-amount or out of window and has an unrecognised status is ignored once. Which reason is reported is not output-affecting here.
- **Status words not listed.** `canceled` and `cancelled` both count as cancelled. Words such as `posted pending` or `post` are not split or prefix-matched: only an exact normalised match counts, so they are unrecognised.
- **Status vs. validity.** FORMAT.md lists `posted`, `pending`, `cancelled` as the status values yet says any other word is ignored and counted. **Chosen:** an unknown word is never an input error; it is an ignored row.
- **"The user may choose to count unrecognised rows as posted"** is handled by the importer rewriting the status to `posted`. The cross-check has no such option because it sees only the engine input.

## AMB-25 — R-1.9 typical spending: input handling and counts
- **Input error mechanism.** FORMAT.md says bad `typical` input is "an input error" but gives no `error_code` (the codes are for market-data problems). **Chosen:** `run` raises `ValueError` with a clear message, as it already does for an unknown strategy. No result object is returned. A scenario with both `typical` and `transactions` (even `transactions: []`) is rejected the same way. A key present with value `null` counts as present.
- **Strictness of `per_week`.** "A whole number" is read as a string of digits only, value 1 to 60. `"5.0"`, `"+5"`, `" 5"` and `"05"`-style padding: `"05"` is accepted (digits, value 5), the others are rejected. The spec does not say whether leading zeros are allowed. Non-string JSON numbers are rejected (the format uses strings; the loader also rejects floats).
- **Strictness of `average_roundup`.** Exactly `0.` plus two digits, `0.01` to `0.99`. `0.5`, `1.00`, `.50`, `0.500` are errors. The spec says "exactly two decimals".
- **`typical_purchases` arguments.** Must be real `int`s (a bool is rejected) in range; the dates are ISO strings. A window with end before start returns `[]` rather than an error, because R-1.9 only says purchases count inside [start, end]. The engine would hit `WINDOW_OUTSIDE_DATA` anyway.
- **Counts.** All generated purchases are counted as used (`transactions_used`) and `transactions_ignored` is `"0"`: they are posted debit purchases inside the window by construction, and R-1.9 says nothing else about the summary counts. The $12.xx amounts never trip the non-purchase keyword rule because the description is not generated.
- **Weeks overlapping the window.** "Every week that overlaps the window" is implemented from the Monday on or before `start`; purchases dated outside [start, end] are dropped, not shifted.
- **Ordering.** "By date then by k": since the offset ⌊7k/n⌋ is non-decreasing in k, generation order within a week is already date order, and weeks are ascending. For n > 7 several purchases share a date and keep k order (they are identical tuples anyway).
- **Dates outside market data.** R-1.9 does not restrict purchase dates to the market calendar; purchases on weekends and holidays are generated and handled by the normal batch timing rules (R-5.1).

## AMB-26 — R-13.4 composition of the end value: edge cases
- **Position of `composition` in `summary`.** FORMAT.md describes the field but its output example does not show it, and key order is not specified. **Chosen:** last key of `summary`, after `deepest_dip`. JSON object order should not matter to a consumer; the self-test key-order check was extended to match this choice.
- **Exact amounts vs displayed amounts.** R-13.4 says the shares come from the exact amounts "before any display rounding", and the four parts "together equal the ending value". The displayed `amount` strings are each rounded from their own exact value, so they need not add up to the displayed `ending_value`, and a share may not match the displayed amounts. Example (S3): amounts 2.18 / 0.01 / 0.00 / 0.18 give 9192 / 42 / 0 / 766 because the exact parts are 24/11, 0.01 and 2/11. **Chosen:** shares from exact Fractions only.
- **Which exact value is each part.** `shares` = exact holdings value (shares × last close on or before `end`, R-13.1, not the 6-decimal displayed share count); the other three are the exact values already used for `roundups_waiting`, `dividends_as_cash` and `receivables`. The total used as the divisor is the sum of the four, which R-13.1 makes equal to the ending value.
- **"Largest fractional remainders".** Read as the remainder of each part's exact share after its floor (a value in [0, 1)), compared exactly. The leftover is 0 to 3 points, so each part gets at most one extra. A part whose exact share is a whole number has remainder 0 and is last in line; it can still receive a point only if every part ahead of it is already served, which cannot happen because the leftover is below the number of parts with a non-zero remainder.
- **Ties.** Exact ties (e.g. three equal thirds, or 6/7 against 3/28 which share the remainder .428571) go to the earlier part in the fixed order, as the rule says. The tie-break is among remainders only, not among parts with equal amounts.
- **Ending value $0 vs negative.** The rule says all four are 0 when the ending value is $0. The parts are never negative, so a negative total cannot occur; the code treats any total <= 0 as the zero case. Exactly $0 means the exact value, not the displayed "0.00": an ending value of 0.004 displays as 0.00 but is above zero, so the shares still add to 10,000. **Chosen:** exact test.
- **Type of `share_bp`.** An integer in JSON, not a string, as FORMAT.md says "integer", although other summary counts (e.g. `roundup_buys`) are strings.
