# RoundUp — Finance Rules

Every rule the simulation engine follows, with the reason. Rules are numbered so tests and code can cite them (`R-3.2`). Anything marked **OPEN** is undecided and must not be implemented until resolved (see OPEN-QUESTIONS.md). §15 records the independent review. §16 lists what changed in revision 2. §17 lists the defaults chosen on the owner's behalf, for confirmation.

**Revision 2 (2026-10-12).** The owner's decisions are applied: portfolio demo; threshold $5 is the default; VOO and SCHD from 2012. Conservative defaults now fill the remaining open items.

Scope reminder: RoundUp is a hypothetical, historical simulation. No money moves, nothing is a forecast, nothing is advice.

---

## 0. Number handling (applies everywhere)

| # | Rule | Reason |
|---|------|--------|
| R-0.1 | All money inputs are parsed from strings into integer cents. An amount with more than two decimal places is **rejected** at import, not rounded. | Floats cannot represent most cent values exactly; silent rounding of inputs hides data errors. |
| R-0.2 | Cash flows that originate from the user (purchases, round-ups) are integer cents. | They are real-world cent amounts. |
| R-0.3 | Derived quantities (shares, dividend cash, valuations) are `decimal.Decimal` in a fixed context: precision 28 significant digits, `ROUND_HALF_EVEN`. The only rounding inside the engine is the context's rounding at 28 significant digits (e.g. `cash ÷ price` never terminates). No intermediate value is quantized to cents or to a share precision. | Rounding to cents at each step accumulates drift and makes results depend on step order. Rounding at 28 digits is far below any displayed digit. |
| R-0.4 | Rounding to display precision happens only at output: money to the nearest cent (`ROUND_HALF_EVEN`), shares to 6 decimal places. The engine returns the exact value and the display value. Each displayed figure is rounded from its own exact value, so displayed components can differ from a displayed total by $0.01. The UI says so where components are summed. Before display rounding, a value is first rounded to 20 decimal places. That removes the ≤ 1e-24 residue of 28-digit division, so an exact half-cent tie (e.g. 9.485) still rounds half-even (9.48), not up. Found by the independent cross-check (scenario R-5288). | One rounding point means one tolerance to test against. Half-even avoids upward bias across many values. |
| R-0.5 | Floats are forbidden in the engine and in ingestion. (a) The engine's Decimal context **traps `FloatOperation`**. (b) Prices, dividend amounts and split ratios are parsed from **strings** at ingestion, e.g. JSON with `parse_float=Decimal`, CSV as text. (c) A lint test rejects float literals and `float(` in these packages. | Project brief. Python docs: with the trap set, "All other mixed operations raise `FloatOperation`". `Decimal(float('1.1'))` becomes `1.100000000000000088817841970012523233890533447265625` ([docs.python.org/3/library/decimal.html](https://docs.python.org/3/library/decimal.html)). A grep for `float(` does not catch `json.loads`, so (b) is needed. |
| R-0.6 | Currency is USD only. | All candidate funds trade in USD; FX is out of scope. |

## 1. Transactions and import

| # | Rule | Reason |
|---|------|--------|
| R-1.1 | A transaction has: **date**, amount (cents, > 0), direction (debit/credit), status (posted/pending), category (purchase / non-purchase), description, optional external ID and optional account label. | Bank exports usually carry only a date. We must not invent a time. |
| R-1.2 | **Date used** = the posted date if the file has one; otherwise its single date column. The import summary records which column was used. Dates are calendar dates with no timezone conversion. | Owner decision. Posted is when the purchase is final (consistent with R-1.4). Timezone is harmless to R-5.1: the end of local day D in any zone from UTC−12 to UTC+14 falls before 16:00 New York time on D+1. |
| R-1.3 | **Sign convention** is inferred per file from its headers or labels (e.g. separate Debit/Credit columns, a Type column). If it cannot be inferred, the user must choose it explicitly before import. There is no silent default. | Card exports often show purchases as positive and bank exports as negative. A wrong default flips the whole file. |
| R-1.4 | Only **posted debits categorised as purchases** generate round-ups. Pending rows, credits, and non-purchase debits are ignored: card payments, transfers in or out, ATM withdrawals, peer-to-peer sends, loan payments and fees. A debit is a non-purchase if (a) its type field (normalized as in R-4.5) is one of `payment`, `transfer`, `atm`, `fee`, `interest`, `loan`; or (b) its normalized description contains one of these **whole words**: `payment`, `transfer`, `xfer`, `atm`, `withdrawal`, `zelle`, `venmo`, `autopay`, `loan`, `fee`, `interest`, or the phrase `cash app`. A whole word is a run of letters and digits. So `coffee` does not match `fee`. Every ignored row is listed in the import summary with its reason, and the user can reclassify any row. | Round-up products round card purchases. Rounding a credit-card payment from a checking export double-counts purchases already rounded from the card export. |
| R-1.5 | Zero-amount rows are ignored and listed. | R-2.1 needs A > 0. |
| R-1.6 | Rows dated before the scenario start or after its end are excluded and counted in the summary. | Keeps the window well defined. |
| R-1.7 | Generated (synthetic) transactions are always posted purchases, in cents, from a seeded generator. The seed is saved with the scenario. | Reproducibility. |
| R-1.8 | A refund (a credit) never creates a round-up. | Owner decision. Only purchases round up (R-1.4). |

## 2. Round-up definition

| # | Rule | Reason |
|---|------|--------|
| R-2.1 | For a purchase of `A` cents (`A > 0`): `roundup = (100 − (A mod 100)) mod 100`. | Exact integer arithmetic; "round up to the next dollar". |
| R-2.2 | A whole-dollar purchase (e.g. $4.00) produces a **$0.00** round-up. | Owner decision. It is already at a dollar; "next dollar" would invent a $1.00 contribution the user never had as spare change. Some products choose $1.00 instead; we choose the literal definition and state it in the assumptions panel. |
| R-2.3 | Round-up multipliers and minimum/maximum caps are **not** in v1. | Keeps v1 rules small. They can be added later as a strategy parameter without changing R-2.1. |

## 3. Refunds and reversals

| # | Rule | Reason |
|---|------|--------|
| R-3.1 | A refund is a credit and does **not** reverse or reduce any round-up, whether or not that round-up has already been invested. | Owner decision. In round-up products the round-up is a separate transfer from the user's account; a merchant refund returns the purchase amount, not the spare change. Reversing would also require linking refunds to purchases, which CSVs do not reliably support. |
| R-3.2 | A purchase explicitly marked cancelled or voided before posting is excluded and produces no round-up. | It never posted (R-1.4). |
| R-3.3 | The engine never sells shares. | No reversal exists (R-3.1). Selling would introduce realized-gain and tax logic, which is out of scope. |

## 4. Duplicates

| # | Rule | Reason |
|---|------|--------|
| R-4.1 | If rows carry an external transaction ID, rows with the same ID and account label are the same transaction. If their amounts or dates differ (e.g. a tip added after authorisation), the row from the **most recently imported file** is kept and the change is flagged. Within one file, the later row wins. | IDs are the only reliable identity. The latest version reflects the final posted amount. |
| R-4.2 | Without IDs, rows identical on (date, amount, direction, normalized description, account label) **within one file** are flagged as possible duplicates but **kept** by default. | Two identical coffees on one day are legitimate. Silently dropping real purchases is worse than flagging. |
| R-4.3 | Across files, if a new file for the same account label **overlaps the date range** of an earlier file, rows in the overlap that match existing rows on the R-4.2 key are **excluded by default**, and the user is shown the count and can keep them. | Overlapping exports (Jan–Mar then Mar–May) would otherwise count March twice. |
| R-4.4 | Re-importing a file with the same content hash into the same scenario is blocked. The hash is SHA-256 over the file's rows after mapping to fields, serialized canonically. | The most common duplication. Hashing mapped rows, not bytes, catches the same export saved with different line endings. |
| R-4.5 | Normalized description = trimmed, case-folded, internal whitespace collapsed. | Exports vary in casing and spacing. |

## 5. When a round-up invests (timing)

Definitions. A **session** for a fund is a day when the exchange calendar shows the market open **and** that fund has an official close (R-5.6). A **calendar-open day** is a day the exchange calendar shows open.

| # | Rule | Reason |
|---|------|--------|
| R-5.1 | Every strategy groups round-ups into **batches**, each with a **cut-off date C**. A batch is bought at the **official close of the fund's first session strictly after C**. Batch = every non-zero round-up dated ≤ C that is not already in an earlier batch. The whole batch is bought. A batch of $0.00 is never created. Each batch is **one buy**, even if two batches execute at the same close. | Transactions have no time of day. A same-day close could come before the purchase (e.g. a 9 pm purchase), which is look-ahead. The next session's close is always after the cut-off and is a single, published, reproducible price. |
| R-5.2 | **Strategies.** **Threshold (default, $5.00):** C = the first purchase date on which the unbatched total reaches ≥ $5.00, counting **all** purchases on that date. The excess is not carried over. The next batch starts from C+1. **Next session:** C = each purchase date (one batch per date). **Weekly:** weeks run Monday–Sunday inclusive; C = that Sunday. **Monthly:** C = the last calendar day of the month. The threshold amount is fixed at $5.00 in v1. | Owner decision: invest when round-ups reach $5. The other three remain as comparison options, because timing is a core lesson. Each cut-off is knowable at C. Batches are disjoint and complete, so no round-up is counted twice or lost. |
| R-5.3 | Until bought, round-ups are **uninvested cash earning 0%**. They count in total value at face value from their purchase date onward. | Honest representation of money waiting to be invested. Interest on cash is out of scope (§14). |
| R-5.4 | Any round-up or batch whose execution session would be **after the scenario end date** (or after the last available close) stays uninvested cash in the ending value. That covers purchases on the last days, complete batches not yet executed, and partial batches. | Buying after the end date would use data outside the window. |
| R-5.5 | Strategies that need future information are **prohibited**, e.g. "invest the year's round-ups on Jan 1" or "buy at the month's low". | Look-ahead. |
| R-5.6 | Weekends, exchange holidays and unscheduled closures are not calendar-open days. Early-close days are sessions, and their official close is used. | The calendar is a cross-check, so missing data is not mistaken for a holiday (R-6.2). |
| R-5.7 | A scenario with N funds is **N independent single-fund runs** on the same transaction set. Each fund's sessions are computed independently. No allocation or rebalancing between funds. | Clean comparison. Multi-fund portfolios are out of scope (§14). |

## 6. Missing prices and data gaps

| # | Rule | Reason |
|---|------|--------|
| R-6.1 | An execution never uses a price dated on or before the purchase (or cut-off) date, and never interpolates or forward-fills a price for **execution**. | Executing at an earlier, already-known price is backdating (stale-price bias), and it can flatter or hurt results. Interpolated prices never traded. |
| R-6.2 | A **data gap** is a calendar-open day with no close for that fund. If the first calendar-open day after D is a data gap, execution moves to the next session (R-5.1 already implies this), and the trade is flagged `delayed_by_data_gap`. | Makes the substitution visible. The flag condition is stated, so every implementation sets it the same way. |
| R-6.3 | A run **fails** with a data-quality error, instead of producing results, if (a) inside its window a fund has a data gap of more than 3 consecutive calendar-open days (4 or more), or (b) **anywhere in the market input** a split or dividend ex-date on or before the data end has no close (events after the data end are "no data yet", R-6.5). Also data errors, anywhere in the input: (c) a split or dividend whose ex-date is not a calendar-open day, or a close dated on a day that is not calendar-open. Error codes and precedence: engine/fixtures/FORMAT.md. | (a) A long gap means bad data, not a closed market. (b) Valuing across a corporate action with a stale price double-counts it: a split multiplies shares but the carried price is pre-split, and a dividend receivable is added but the carried price has not dropped. |
| R-6.4 | For **valuation only** on other data-gap days, the last close is carried forward, and the point is marked as carried. No trade ever uses a carried price. | Charts need a value every calendar-open day. R-6.3(b) makes carrying safe. |
| R-6.5 | The data end is the last close that passed ingestion checks. Calendar-open days after it are "no data yet", not data gaps. | Prevents a provider's normal overnight delay from failing every scenario. |

## 7. Prices and dividends — the no-double-counting rule

**Decision: raw (unadjusted) closing prices plus explicit dividend and split events. The engine never uses dividend-adjusted prices.**

| # | Rule | Reason |
|---|------|--------|
| R-7.1 | Purchases and valuations use the **raw official closing market price**: the price as printed that day, adjusted for **neither** splits **nor** dividends. | That is the price a buyer actually paid that day. |
| R-7.2 | Dividends enter **only** as explicit cash events (ex-date, pay date, cash amount per share). | One source of dividend value. |
| R-7.3 | Dividend-adjusted ("adjusted close", "total return") price series are **never** used in the engine. Using them together with R-7.2 would count every dividend twice. | Prevents double-counting. |
| R-7.4 | Splits enter only as explicit split events: ex-date and ratio = new shares ÷ old shares (2-for-1 = 2; reverse 1-for-4 = 0.25; fractions are kept, so there is no cash in lieu). Dividend per-share amounts must be on the **same share basis as the raw price on their ex-date**, not retroactively split-adjusted. | Raw prices plus split events don't need rewriting when a later split happens. Basis consistency prevents mis-scaled dividends. |
| R-7.5 | **The engine verifies the price basis** of the whole series it is given, before any run. For each split with ratio r and ex-date X, let P = the close of the last session before X and Q = the close on X. Then define `jump(a, b) = max(a/b, b/a)`. The series is raw across the split if `jump(Q·r, P) < jump(Q, P)`, i.e. undoing the split makes the day's move smaller. Otherwise the series is split-adjusted and is **rejected**. The series is also rejected if there is no close at P or Q, or if r ≤ 0 or r = 1. Dividend amounts must be supplied on the raw basis (field `amount_raw`). Adapters convert or reject. | Many sources label a split-adjusted series "Close". Applying split events to it multiplies pre-split holdings twice. |
| R-7.6 | Why raw + events instead of adjusted prices: (a) adjusted series are **rewritten retroactively** at every new dividend or split; (b) adjustment methods differ by provider; (c) explicit events let users see each dividend and turn reinvestment on or off; (d) the AI explainer can cite specific dividend amounts; (e) an adjusted price at a past date embeds dividends paid *after* that date, so nobody ever traded at it. Raw data still gets occasional corrections; saved results are protected by R-12.4. | Reproducibility, transparency and testability. The cost is extra engine logic (ex-date and pay-date handling), covered by golden tests. |
| R-7.7 | **Applies from the data stage, not to the engine or demo sample data.** The pipeline cross-checks events against the provider's adjusted series. For each fund and calendar year, a buy-and-hold of one share is computed from raw closes and our events, **reinvesting at the ex-date close** (the convention most adjusted series use; check-only, not the engine rule). It is compared with the adjusted-close return. A difference beyond tolerance blocks that fund's data. The adjusted series is used **only** here. Tolerance is decided from the first real backfill (OPEN-QUESTIONS.md). | Independent detection of missing or wrong events. Matching the adjusted series' reinvestment convention avoids a built-in systematic difference. |
| R-7.8 | Prices are the ETF **market** close, not NAV. | Investors buy ETFs at market prices. |

## 8. Dividends: entitlement, timing and reinvestment

| # | Rule | Reason |
|---|------|--------|
| R-8.1 | **Order of processing within a session:** (1) apply splits whose ex-date is today to held shares; (2) fix dividend entitlements for dividends whose ex-date is today; (3) execute buys at today's close (round-ups and dividend reinvestments); (4) value at today's close. | A stated order removes the same-day ambiguities. Every implementation then gets the same numbers. |
| R-8.2 | **Entitlement:** a dividend with ex-date X is earned on the shares held at the **close of the session before X**, after applying any splits with ex-date ≤ X. That converts them to the dividend's basis (R-7.4). Shares bought at the close of X or later earn nothing for it. | Trading on or after the ex-date is "ex" (without) the dividend. FINRA Rule 11140(b)(1): for distributions under 25% of the security's value, "the date designated as the "ex-dividend date" shall be the record date if the record date falls on a business day" ([finra.org/rules-guidance/rulebooks/finra-rules/11140](https://www.finra.org/rules-guidance/rulebooks/finra-rules/11140)). That reflects T+1 settlement, "As of May 2024" ([FINRA](https://www.finra.org/investors/insights/understanding-settlement-cycles)). Our buys execute at a close, so a buy at the close of the session before X settles by the record date and is entitled. |
| R-8.3 | **Dividend cash** = entitled shares (R-8.2, exact Decimal) × cash amount per share. It is **fixed on the ex-date** as an immutable receivable. Splits and buys between the ex-date and the pay date do not change it. If entitled shares are zero, no receivable is created and nothing is counted. | Removes the "shares at which date?" ambiguity, which could double the amount across a split. |
| R-8.4 | From ex-date to pay date, the receivable counts in total value at face value. | The raw price drops by roughly the dividend on the ex-date. Without the receivable, the chart would show an artificial loss until the payment. |
| R-8.5 | **Default: dividends are reinvested** at the close of the fund's first session on or after the pay date, buying the same fund. Each reinvestment is one dividend buy. Before the pay date the amount is a **receivable**. From the pay date until it is reinvested it is **cash**. If the reinvestment session is after the scenario end, it stays cash in the ending value. If the first calendar-open day on or after the pay date is a data gap, the buy is flagged `delayed_by_data_gap`. | Owner decision (reinvest by default, with a toggle). It approximates a dividend reinvestment plan; brokers' actual timing and price vary. The cash does not exist until the pay date. |
| R-8.6 | Users can switch reinvestment off per scenario (toggle; default on). Paid dividends then accumulate as cash at 0%. | Shows the effect of reinvestment, one of the core lessons. |
| R-8.7 | Special distributions and capital-gains distributions supplied as cash events are treated like ordinary dividends. Return-of-capital classification is ignored. Any event with ex-date **after** its pay date (due-bill case for very large distributions) is flagged and blocks ingestion for manual review. | Classification only matters for tax (out of scope). FINRA Rule 11140(b)(2): for distributions "25 percent or greater of the value of the subject security, the ex-dividend date shall be the first business day following the payable date". That breaks R-8.2's ordering assumption. |
| R-8.8 | A dividend event **without a pay date is rejected** (a data error). The engine never estimates a pay date and never reinvests at the ex-date. | Conservative default (§17). Estimating dates invents data. Ex-date reinvestment uses cash before it exists. A provider without pay dates needs an adapter that sources real pay dates. |

## 9. Fractional shares

| # | Rule | Reason |
|---|------|--------|
| R-9.1 | Fractional shares are allowed with no minimum purchase. Shares bought = cash ÷ price (Decimal, R-0.3). | Round-ups are cents; whole-share-only buying would leave most money uninvested and misrepresent round-up products. |
| R-9.2 | Displayed share counts are rounded to 6 decimal places; internal counts are not. | Readability without drift. |

## 10. Fees and costs

| # | Rule | Reason |
|---|------|--------|
| R-10.1 | The **expense ratio is not subtracted**. Fund expenses are accrued daily against fund assets, so they are already in the NAV and hence in the market price. Subtracting again would double-count. | Prevents double-counting. |
| R-10.2 | The expense ratio is **shown** on each fund card and in the assumptions panel, with its source and "as of" date. A plain illustration accompanies it: "about $X a year on every $10,000, already included in the price". | The brief asks to show how fees affect outcomes. It is shown as context, so the maths stays honest. |
| R-10.3 | Historical expense-ratio changes are not modelled. | Not needed for the maths (R-10.1). |
| R-10.4 | Commissions, bid–ask spread, round-up app subscription fees and account fees are **not modelled** in v1, and this is disclosed. | Conservative default (§17). A fee option would need its own rules (what happens when cash cannot cover the fee) and another review. |

## 11. Look-ahead and other biases

| # | Rule | Reason |
|---|------|--------|
| R-11.1 | Every strategy decision uses only information dated on or before its cut-off date. Every execution price is dated strictly after it (R-5.1, R-5.2, R-6.1). | Definition of no look-ahead. |
| R-11.2 | The engine is event-driven and processes days in order. Property test: for **successful runs on the same market-data input**, truncating market data after date T does not change any output dated ≤ T. | Mechanical guard against look-ahead bugs. Scoped so data-quality failures (R-6.3) do not contradict it. |
| R-11.3 | The funds were chosen with hindsight: they exist and are popular today. This **selection/survivorship bias** is disclosed in the assumptions panel and in the explainer's fixed caveats. | It cannot be engineered away, so it must be stated. |
| R-11.4 | No projection beyond the last available close is ever computed. | Brief: nothing is a forecast. |

## 12. Fund coverage, scenario dates and data versions

| # | Rule | Reason |
|---|------|--------|
| R-12.1 | A scenario's window [start, end] must satisfy: start ≥ the fund's first close, and end ≤ the fund's last close (the data end). Otherwise the scenario is rejected with a message naming the fund and its available range. | Holding cash until a fund exists would mix cash drag into fund comparisons. |
| R-12.2 | v1 funds: **VOO and SCHD**, from the first session of 2012 (2012-01-03; Jan 2 was the observed New Year holiday). Both funds started before 2012 (DATA-SOURCES.md). Each fund's real data coverage is checked at ingestion. | Owner decision. VOO's 2013 reverse split and SCHD's 2024 forward split are both golden tests. |
| R-12.3 | Results show an "as of" date equal to the last close used. | Users must know how current the numbers are. |
| R-12.4 | Each saved scenario **stores its own computed results**, with the data end used, the engine version and a SHA-256 checksum of the market-data input. Opening it shows the stored results. Re-running uses current data and says if the numbers changed. No dataset versioning in v1. | Owner decision (simplified demo). Saved results stay stable without versioning machinery. Trade-off: a past run cannot be recomputed exactly after a data correction. The checksum shows *that* inputs changed, not what changed. |
| R-12.5 | **Demo mode.** The engine runs on any price series that passes R-6/R-7 validation. A series is either *real* (from a licensed provider) or *sample* (illustrative), and every result carries that label. Sample series must be labelled "Illustrative sample data — not real prices" wherever their results are shown. | The public demo may only use data whose terms allow it (DATA-SOURCES.md). Labelling prevents sample results from being read as real history. |

## 13. Reported results (per fund run)

| # | Rule | Reason |
|---|------|--------|
| R-13.1 | Reported, as of the end date: total round-ups contributed; round-up buys (count of batches executed); dividend buys (count); **dividends earned** (ex-date ≤ end); **dividends paid** (pay date ≤ end); shares held; holdings value = shares × the last close on or before end; uninvested cash (round-ups not yet bought + dividend cash not yet reinvested); receivables (dividends earned, pay date > end); ending value = holdings + uninvested cash + receivables; gain = ending value − contributed; gain % = gain ÷ contributed × 100, shown to 2 decimal places (half-even), or "n/a" when contributed is $0. | Simple, explainable numbers with every edge defined. |
| R-13.2 | The daily value series has one point per calendar-open day in the window. It uses that day's close, or the carried close on gap days (R-6.4). The first point may carry a close from before the window. | — |
| R-13.3 | No annualized return (XIRR) in v1. | Conservative default (§17). It is easy to misread as an expected future return, and hard to explain. |

## 14. Out of scope (v1)

Taxes of any kind (dividends are treated as if in a tax-free account; this is disclosed); inflation adjustment; interest on cash; bank-transfer settlement delays; selling or withdrawals; rebalancing or multi-fund portfolios; non-USD currency; intraday prices; forecasts; any recommendation.

## 15. Review log

An independent reviewer saw only the first draft of this file (its rule numbers differ in places) and was asked to find ambiguity, double-counting and look-ahead. Resolutions:

| Finding | Severity | Resolution |
|---|---|---|
| Carry-forward valuation across a split or ex-dividend on a gap day double-counts | High | **Accepted**: R-6.3(b) fails the run. Reviewer offered price adjustment as an alternative; failing was chosen as simpler and very rare for these funds. |
| "Shares held" for dividends had no date; a split before the pay date could double the amount | High | **Accepted**: R-8.2, R-8.3 fix it at ex-date, immutable. |
| Same-day split + dividend used mismatched share bases | High | **Accepted**: R-8.1 order of processing, R-8.2 basis conversion. |
| "Raw close" undefined; split-adjusted "Close" + split events double-applies | High | **Accepted**: R-7.1 definition, R-7.5 ingestion check. |
| Card payments, transfers and ATM debits generated round-ups | High | **Accepted**: R-1.4. |
| Truncation property contradicts gap-failure rule | Medium | **Accepted**: R-11.2 scoped; R-6.5 adds "no data yet". |
| End-of-window handling covered only partial batches | Medium | **Accepted**: R-5.4 broadened; R-1.6 adds out-of-window rows. |
| Weekly week definition ambiguous | Medium | **Accepted**: Monday–Sunday. |
| Threshold batch semantics underspecified | Medium | **Accepted**: R-5.2 defines batch membership. |
| No rule for transaction vs posted date | Medium | **Accepted**: R-1.2 uses posted date. Timezone argument recorded. |
| Sign-convention default contradicted its own reason | Medium | **Accepted**: R-1.3, no silent default. |
| Overlapping exports double-count | Medium | **Accepted**: R-4.3. Same-ID/different-amount rule added to R-4.1. |
| "Not rounded" claim false at precision 28; ingestion floats | Medium | **Accepted**: R-0.3 reworded, R-0.5(b). |
| Multi-fund semantics contradicted out-of-scope list | Medium | **Accepted**: R-5.7. |
| Dividends crossing end date; "received" undefined | Medium | **Accepted**: R-8.5, R-13.1 earned vs paid. |
| Data revisions silently change saved scenarios | Medium | **Accepted**: R-12.4 dataset versions. |
| Low items: zero amounts, gain % ÷ 0, rounding sums, mislabelled reason in R-6.1, gap flag condition, split ratio format, "only immutable" overstated, cross-check convention, due bills, "DRIP" overstated, "paid" vs "accrued" | Low | **All accepted**. Applied in R-1.5, R-13.1, R-0.4, R-6.1, R-6.2, R-7.4, R-7.6, R-7.7, R-8.7, R-8.5, R-10.1. |
| R-7.7 cross-check: reviewer suggested widening the tolerance to absorb pay-date vs ex-date reinvestment drift | — | **Partly disagreed.** Instead, the check computes with ex-date reinvestment, matching the adjusted series' convention, so the tolerance can stay tight. |

The reviewer worked without web access to official sources. Their market-convention statements (ex-date mechanics under T+1, due bills) were taken as review input, not as verified citations. The ex-date rules were then verified against FINRA Rule 11140 (cited in R-8.2 and R-8.7). Both of the reviewer's claims held.

## 16. Changes in revision 2

| Change | Rules | Why |
|---|---|---|
| The default strategy is the $5 threshold; the others become comparison options; batching is defined for all strategies; a $0 batch is never created; buy counting is defined | R-5.1, R-5.2 | Owner decision. Precise enough for an independent implementation. |
| Refunds never create round-ups (explicit) | R-1.8 | Owner decision (previously implied by R-1.4). |
| The non-purchase keyword list is published in the rules | R-1.4 | Both implementations need to classify identically; it is also transparent to users. |
| The split-basis check is an exact inequality, and it is run by the engine | R-7.5 | "Roughly 1/ratio" was not testable. |
| Ex-date on a non-calendar day, or a close on a closed day, is a data error; a missing close on an event ex-date fails the run wherever it is in the input | R-6.3 | Missing cases. Whole-input checking also makes the R-7.5 basis check well defined (it needs closes on both sides). |
| A zero-share dividend creates no receivable | R-8.3 | Defines `dividends_earned` and buy counts for events before the first purchase. |
| Dividend timing: receivable before the pay date, cash after | R-8.5 | It was ambiguous whether paid-but-unreinvested money was a receivable or cash. |
| Dataset versioning replaced by per-scenario stored results + checksum | R-12.4 | Owner decision (simplified demo). |
| Demo mode and sample-data labelling | R-12.5 | Data licensing for a free demo. |
| VOO + SCHD from 2012 | R-12.2 | Owner decision. |
| R-8.8, R-10.4, R-13.3 decided conservatively | — | §17. |

## 17. Defaults chosen on the owner's behalf (please confirm)

The owner asked for the most conservative reasonable default on every open item they did not answer.

| Item | Default | Why it is the conservative choice |
|---|---|---|
| Dividend without a pay date (R-8.8) | Reject the event; never estimate | Inventing dates or reinvesting early would overstate results without the user knowing. |
| App or subscription fee (R-10.4) | Not modelled; disclosed | Avoids unreviewed rules. The disclosure tells users real apps may charge fees. |
| Annualized return (R-13.3) | Not shown | It is the figure most easily mistaken for a forecast. |
| Duplicate rows within one file (R-4.2) | Keep and flag | Never silently drop a real purchase. |
| Overlapping files (R-4.3) | Exclude matches by default, user can keep | Never silently double-count. |
| Interest on cash (§14) | None | Does not invent returns. |
| Threshold amount | Fixed at $5.00 | Owner's stated rule; making it configurable adds test surface. |
| Gap tolerance (R-6.3) | Fail at 4+ consecutive missing days | Prefers no answer over a wrong answer. |
| Adjusted-series tolerance (R-7.7) | Decided from first real backfill; until then real data is not published | Not decidable without data. |
