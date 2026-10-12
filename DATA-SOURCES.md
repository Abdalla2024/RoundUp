# RoundUp — Data Sources

All pages accessed **2026-10-12**. Quotes are verbatim from the URL given. "Verified" means checked directly from the official page or a live call. **UNVERIFIED** means it could not be confirmed and nothing may be decided on it. Licence facts change: re-check before signing anything.

## 1. What we need

- Daily **raw** closes (not split- or dividend-adjusted) for VOO, VTI, SCHD and VYM, 2012-01-03 → present (FINANCE-RULES R-7.1).
- Dividend events with **ex-date, pay date, cash amount on the raw basis** (R-7.2, R-7.4, R-8.5).
- Split events (ex-date, ratio) (R-7.4).
- An adjusted-close series, **for the cross-check only** (R-7.7).
- Rights: **store** in our Postgres, and **display** derived numbers and charts on a **public** site (free at first, possibly monetized later).

## 2. Fund facts (verified)

| Fund | Inception | Expense ratio | Distributions | Source |
|---|---|---|---|---|
| VOO | 2010-09-07 | 0.03% ("As reported in the most recent prospectus"; fact sheet as of June 30, 2026) | Quarterly | [Vanguard fact sheet F0968](https://fund-docs.vanguard.com/F0968.pdf) |
| VTI | 2001-05-24 | 0.03% (same basis) | Quarterly | [F0970](https://fund-docs.vanguard.com/F0970.pdf) |
| VYM | 2006-11-10 | 0.04% (same basis) | Quarterly | [F0923](https://fund-docs.vanguard.com/F0923.pdf) |
| SCHD | 2011-10-20 | 0.06% (summary prospectus dated Feb 27, 2026) | Quarterly income; capital gains annually if any | [SEC N-CSRS](https://www.sec.gov/Archives/edgar/data/1454889/000119312525109655/d894308dncsrs.htm), [SEC 497K](https://www.sec.gov/Archives/edgar/data/1454889/000110465926020681/tm266454-15_497k.htm) |

**Consequences for the plan:**
- All four funds started before 2012-01-01, so a 2012 start works for each. Each fund's actual data coverage from our provider must still be checked at ingestion (R-12.1).
- **VOO 1-for-2 reverse split, 2013-10-24.** "Adjusted to reflect a 1-for-2 reverse share split as of the close of business on October 24, 2013." I verified the text myself in the [SEC 485BPOS](https://www.sec.gov/Archives/edgar/data/36405/000093247114005363/indexfunds485bfinal.htm).
- **SCHD 3-for-1 split.** "Shares will begin trading at their post-split price on October 11, 2024." ([Schwab press release](https://pressroom.aboutschwab.com/press-releases/press-release/2024/Schwab-Asset-Management-Announces-ETF-Share-Splits/default.aspx)).
- So split handling is a v1 requirement, not an edge case.
- **VTI index rename.** On 2026-07-29 the fund names gained "Morningstar", following the index rebrand. Vanguard says the change "will not affect the funds' investment objectives or how they are managed" ([Vanguard press release](https://corporate.vanguard.com/content/corporatesite/us/en/corp/who-we-are/pressroom/press-release-vanguard-to-update-names-of-us-equity-index-funds-tracking-morningstar-indexes-042926.html)). The UI shows the current fund name. The exact new index name is **UNVERIFIED**.
- A March 2026 Vanguard split release covered five other ETFs (VUG, MGK, VOOG, VO, VGT), not VOO, VTI or VYM.
- Historical expense ratios since 2012: **not researched** and not needed (R-10.3).

**Market calendar.** All three historical closures we checked are in both `exchange_calendars` (XNYS) and `pandas_market_calendars` (NYSE): Hurricane Sandy 2012-10-29/30, 2018-12-05 and 2025-01-09. Both libraries were checked on their `master` branches. The release we pin must be re-verified.
- Official confirmation of the closures: [SEC Rel. 34-68138](https://www.sec.gov/files/rules/sro/nysemkt/2012/34-68138.pdf), the [ICE 2018 release](https://ir.theice.com/press/news-details/2018/New-York-Stock-Exchange-to-Honor-President-George-H-W-Bush/default.aspx) and the [ICE 2024 release](https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx).
- The [NYSE holidays page](https://www.nyse.com/markets/hours-calendars) lists only 2026–2028. There is no single official historical list.
- **Choice:** `exchange_calendars`, pinned, as the calendar cross-check (R-5.6).

## 3. Provider comparison

| | Tiingo | EODHD | Alpha Vantage | Massive (ex-Polygon) | FMP |
|---|---|---|---|---|---|
| Free tier reaches 2012 | Yes ("30+ Years") | No (1 yr) | No (latest 100 points) | No (2 yrs) | No (5 yrs) |
| Free-tier rate limit | 50 req/hr, 1,000/day | 20 calls/day | 25 req/day | 5 calls/min | 250 calls/day |
| Store in our DB | **Free: forbidden.** Paid: allowed | Personal: allowed for "private, non-commercial purposes" | Not addressed (UNVERIFIED) | Business: yes | Allowed with conditions |
| Public display | Only with a redistribution licence | Not on any published plan; Custom by quote | Personal, non-commercial only; commercial = contact sales | Business plan only | Needs a separate display agreement |
| Cheapest published price allowing public display | **$250/mo** "for startups" | **None published** ("Custom… from $399.00/mo") | None published | $2,499/mo | None published |
| Raw close | Yes (`close`) | Yes (`close`, "as traded — not adjusted") | Yes (TIME_SERIES_DAILY, "raw (as-traded)") | Split-adjusted by default; `adjusted=false` | "non-split-adjusted" endpoint; fields UNVERIFIED |
| Dividend pay date | **No** (ex-date only) | **Yes** (`paymentDate`) | Yes (DIVIDENDS endpoint, premium for history) | Yes (`pay_date`) | Yes (fields UNVERIFIED) |
| Dividend on raw basis | `divCash` on ex-date | `unadjustedValue` | `amount` | `cash_amount` | UNVERIFIED |
| Adjusted close (cross-check) | Yes, CRSP method (splits + dividends) | Yes (splits + dividends) | Premium; method UNVERIFIED | No dividend-adjusted close | Yes |
| Coverage of our 4 ETFs verified | UNVERIFIED (no keyless demo) | **VTI verified** (live demo); others UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |

Twelve Data was also checked. Free is "Internal non-display usage". External display needs the Venture plan, and the page lists both "$499" and "From $149 /mo", so the price is inconsistent. Its coverage and adjustment details are UNVERIFIED. **Excluded** because it has no advantage over the two leaders.

### 3.1 Tiingo — key passages

- **Storage on free/trial (verified myself, ToS "Last Updated Date: October 6th, 2026"):** "If you use a Starter Plan or any free or paid trial plan … you may not write, save, archive, back up, or otherwise retain Tiingo Data in any persistent or durable storage." ([app.tiingo.com/tos](https://app.tiingo.com/tos) §1.6(a))
- **Display (verified myself):** "All data via the API is for internal consumption only… Redistribution is only available upon special request and permission, and comes with additional fees." (§7.3)
- **Plan tooltip:** "Internal use means you may only use the data for your own personal use and you may not display or share the data with another person or organization." ([tiingo.com/about/pricing](https://www.tiingo.com/about/pricing))
- **Redistribution price:** "EOD + IEX Redistribution | Business | Display Redistribution | … $250/month for startups | $500/month for enterprise". This comes from the product page bundle ([tiingo.com/products/end-of-day-stock-price-data](https://www.tiingo.com/products/end-of-day-stock-price-data)), read by the research subagent. I did not check it directly.
- **Adjustment:** "Both raw prices and adjusted prices are available. The adjustment methodology follows the standard method set forth by… (CRSP)… This methodology incorporates both split and dividend adjustments." `divCash`: "note that "date" will be the "exDate" for the dividend" ([docs](https://www.tiingo.com/documentation/end-of-day)). No pay date is documented.

### 3.2 EODHD — key passages

- **Live demo (verified myself):** `GET https://eodhd.com/api/eod/VTI.US?api_token=demo&from=2012-01-03&to=2012-01-04&fmt=json` returned `{"date":"2012-01-03",…,"close":65.21,"adjusted_close":50.6836,…}`.
  - `GET /api/div/VTI.US?api_token=demo&from=2012-01-01&to=2012-06-30` returned `{"date":"2012-03-26","recordDate":"2012-03-28","paymentDate":"2012-03-30","value":0.308,"unadjustedValue":0.308,…}`.
  - The demo key returns "Forbidden" for VOO (splits endpoint).
- **Fields (verified myself from the docs pages):** `close` is "Closing price, as traded — not adjusted". `adjusted_close` is "Closing price adjusted for both splits and dividends". Dividend `value` is the "Split-adjusted amount", with `unadjustedValue` alongside ([api-for-historical-data](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes), [api-splits-dividends](https://eodhd.com/financial-apis/api-splits-dividends)). We use `unadjustedValue` (R-7.4).
- **Display:** the terms prohibit "Selling, reselling, retransmitting, redistributing, displaying, or granting access to the Information or Services, whether in its original or repackaged form" ([terms](https://eodhd.com/financial-apis/terms-conditions)). Commercial "Internal use" FAQ: "Displaying it or sharing it with people outside your company is not permitted." ([commercial-pricing](https://eodhd.com/commercial-pricing))
- **Storage (personal plans):** "permitted to store, manipulate, and analyze the data for private, non-commercial purposes."
- **Price (verified myself):** Personal "Historian — EOD Historical All-World" $19.99/mo ([pricing](https://eodhd.com/pricing)). Commercial: Custom "Tailored to fit from $399.00 /mo." ([commercial-pricing](https://eodhd.com/commercial-pricing)). The commercial page also lists "Universities & Academic Research licensing", which is worth asking about.

### 3.3 Alpha Vantage — key passages

- "free stock API service covering the majority of our datasets for 25 API requests per day and unlimited API requests for verified open-source or educational projects" ([support](https://www.alphavantage.co/support/)).
- Licence "for personal, non-commercial use, unless you and Alpha Vantage have agreed otherwise in writing" ([ToS](https://www.alphavantage.co/terms_of_service/) §2).
- "The "full" outputsize is available to premium keys" ([documentation](https://www.alphavantage.co/documentation/)). The cheapest premium plan is $49.99/mo ([premium](https://www.alphavantage.co/premium/)).
- **Open question:** whether a free public educational site qualifies for the "educational projects" programme.

### 3.4 Massive (formerly Polygon.io) — key passages

- Individual plans are "exclusively for your personal, non-business, and non-commercial purposes", and you may not use Market Data "to build an application intended for use by end users other than you" ([market-data terms](https://massive.com/legal/market-data-terms-of-service)).
- The Business terms permit display "to Authorized Users or Edge Users within products, services, applications, and websites" ([business terms](https://massive.com/legal/businesses-terms-of-service) §2.2(b)). Stocks Business costs "$2,499/month" ([pricing](https://massive.com/pricing)).
- `adjusted`: "Whether or not the results are adjusted for splits… By default, results are adjusted." This is split-only adjustment.

### 3.5 FMP — key passages

- "Without a specific agreement with FMP, customers are prohibited from showcasing FMP Services or Data on platforms including but not limited to websites… irrespective of whether such usage is complimentary or paid" ([ToS](https://site.financialmodelingprep.com/terms-of-service) §2.2.2).
- Premium "$69" gives "Up to 30 Years of Historical Data" ([pricing](https://site.financialmodelingprep.com/developer/docs/pricing)).

### 3.6 Yahoo Finance / yfinance — excluded

Yahoo's terms prohibit attempts to "access or collect data… from our Services using any automated means… without our express, prior permission". They also say "you may not access or reuse the Services, or any portion thereof, for any commercial purpose" ([legal.yahoo.com](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) §2(d)(ix), §2(e)). yfinance is automated collection, so it is excluded. Only part of the page was read, so any finance-specific supplemental terms are UNVERIFIED.

## 4. Recommendation

**No provider is safe to *publish* with until a licence is confirmed in writing.** The decision rests on licence terms we cannot see (quote-only prices, how "display" and "derived data" are defined), so it is **OPEN** (OPEN-QUESTIONS.md). The recommendation below is conditional.

**Recommended: EODHD, provided its Custom display quote is acceptable.**
- It is the only provider whose data I verified for our exact needs: a raw 2012 close, dividends with **pay date**, and an explicit **unadjusted** dividend value. That matches the finance rules without workarounds. R-8.8 (the no-pay-date fallback) becomes unnecessary.
- Its personal plan ($19.99/mo) explicitly allows storing data for private, non-commercial use. A private development environment is plausibly covered, but that should be confirmed (OQ).
- Risk: the display price is unknown ("from $399/mo").

**Runner-up: Tiingo with the Display Redistribution licence ($250/mo, published).**
- Cheaper and published, and its adjusted series uses a documented method.
- But it has **no dividend pay dates**, which forces R-8.8, and its coverage of our ETFs is unverified.
- Its **free plan forbids storing data at all**, so development would need Power ($30/mo, internal only).

**How to decide:** get written answers to the questions in §6 from both. If EODHD's display quote is ≤ ~$400/mo, choose EODHD. If not, choose Tiingo, decide R-8.8, and get pay dates from issuer distribution histories. Issuer pages as a source are not yet researched and must not be scraped without checking their terms.

## 5. Adapter design (provider is replaceable)

```
roundup_data/
  ports.py        # MarketDataSource protocol (no provider names)
  adapters/eodhd.py, adapters/tiingo.py, adapters/fixture.py
  ingest.py       # provider-agnostic: fetch → validate → version → upsert
  checks.py       # data-quality checks (TEST-STRATEGY §5)
```

```python
class MarketDataSource(Protocol):
    name: str
    def daily_bars(self, symbol: str, start: date, end: date) -> list[RawBar]: ...
    def dividends(self, symbol: str, start: date, end: date) -> list[DividendEvent]: ...
    def splits(self, symbol: str, start: date, end: date) -> list[SplitEvent]: ...
    def adjusted_closes(self, symbol: str, start: date, end: date) -> list[AdjClose]: ...  # cross-check only
    def capabilities(self) -> Capabilities: ...  # e.g. has_pay_date, raw_dividends

@dataclass(frozen=True)
class RawBar:        symbol: str; day: date; close: Decimal; source: str
class DividendEvent: symbol: str; ex_date: date; pay_date: date | None; amount_raw: Decimal; kind: str; source: str
class SplitEvent:    symbol: str; ex_date: date; ratio: Decimal; source: str   # new ÷ old
```

Rules:
- Adapters parse numbers from **strings** into Decimal (JSON `parse_float=Decimal`) (R-0.5). They convert provider basis to raw basis, or raise.
- The engine never imports an adapter. It reads only our versioned tables.
- `capabilities()` makes gaps explicit. Ingestion refuses to publish if `has_pay_date` is false and R-8.8 is undecided.
- **Swapping providers** = new adapter + contract tests on recorded fixtures. Then a parallel run: both providers ingest into a staging dataset version, and every check plus a diff report must pass before switching. A switch creates a new dataset version (R-12.4).
- Attribution text and link per provider are config, shown in the UI footer and the chart captions as the licence requires.
- Licence constraints live in config too (e.g. `may_display_raw_ohlc`, `retention_on_termination`). The UI respects them, e.g. by hiding raw price tables if they are not licensed.

## 6. Questions to send providers before public launch

For **EODHD** (Custom quote) and **Tiingo** (Display Redistribution):
1. Does the licence cover a public website showing charts and numbers derived from EOD data, to anonymous and logged-in users? Does it still apply if we later charge or show ads? What is the price?
2. May we store EOD prices, dividends and splits for VOO, VTI, SCHD and VYM (2012 → present) in our own database? What must be deleted on termination?
3. Are simulated portfolio values "derived data" that we may keep and show after termination?
4. May we show raw closes and dividend amounts in tables, or only charts and derived values? Are user CSV downloads allowed?
5. What attribution is required, and where?
6. Are there exchange fees or subscriber reporting for showing ETF EOD data?
7. Tiingo only: confirm coverage from 2012-01-03 for all four tickers, and whether dividend pay dates are available.
8. Both: may a private, non-public development environment use the cheaper personal or internal plan before the display licence starts?

For **Alpha Vantage**: does a free public educational site qualify for the educational programme, and does that include public display?

## 7. Verification gaps

- Coverage of VOO, SCHD and VYM at either leading provider: UNVERIFIED until we hold a key.
- Tiingo's $250 redistribution price: read by the subagent from the product page's JavaScript bundle. My own attempt to find the string in the bundle failed, so treat it as **UNVERIFIED** until Tiingo confirms it in writing.
- FMP field names, Alpha Vantage's adjustment method, and Twelve Data's details: UNVERIFIED.
- The new VTI index name: UNVERIFIED (doesn't affect the maths).
