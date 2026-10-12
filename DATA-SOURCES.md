# RoundUp — Data Sources

**Revision 2 (2026-10-12).** RoundUp is now a **free, non-commercial, invite-only portfolio demo** (owner decision). This revision redesigns data use around that. §1–3 (needs, fund facts, provider terms) are unchanged research. §4–7 are new.

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

## 4. What the terms allow for a free demo

Based only on the passages quoted in §3:

| Use | Tiingo free | EODHD free | EODHD personal ($19.99/mo) | Alpha Vantage free |
|---|---|---|---|---|
| Reaches 2012 | Yes | No (1 year) | Yes | No (full history is premium) |
| Store in a database | **No**. Only "transiently in volatile memory… only to complete the calculation" (ToS §1.6(a)) | — | Yes: "store, manipulate, and analyze the data for private, non-commercial purposes" | Not addressed |
| Show to other people | **No**. "Internal use… you may not display or share the data with another person" | **No** ("displaying… or granting access" prohibited) | **No** | Personal, non-commercial only; "educational projects" wording is ambiguous |
| Dividend pay dates | **No** (ex-date only), so R-8.8 rejects its dividends | — | Yes | Yes (DIVIDENDS endpoint) |

**Conclusion.** No free or near-free plan we read permits showing results derived from real prices to other people, even invite-only and non-commercial. Whether *simulation results* (not price tables) count as display or redistribution is exactly what the emails in §7 ask. Until a provider says yes in writing, the shared demo uses sample data.

## 5. Demo-mode design

The engine accepts any market series that passes its own validation (FINANCE-RULES R-6, R-7.5, R-8.7, R-8.8). Where the series comes from is outside the engine.

| Mode | Data | Who sees results | Storage | Label |
|---|---|---|---|---|
| **Synthetic scenarios** (shared demo; D-7 as amended by the owner) | Four named market scenarios (steady growth, crash and recovery, sideways, high volatility) × two styles (broad-market, dividend). They are produced by the documented seeded model in [SCENARIO-MODEL.md](SCENARIO-MODEL.md), with quarterly dividends and at least one split per series. No real prices are copied or derived. | Anyone with the invite link | Regenerated deterministically from code + published seeds; nothing stored | "Synthetic scenario. Not a real fund, not real prices, and not a forecast." Symbols are `SYN-…`. A test rejects real ticker names. |
| **Local real** (developer only) | A licensed provider, fetched on the developer's machine | Only the developer | Only as the provider's plan allows (see below). **Never committed** to the repo or used in test fixtures. | "Real data, local only" |
| **Shared real** (future) | A provider that has confirmed in writing (§7) | Invitees | As the written permission allows | Provider attribution as required |

**Local real data, cheapest compliant path.** EODHD personal ($19.99/mo) is the only plan we read that reaches 2012, has pay dates, and allows storage "for private, non-commercial purposes". One month is enough to build and test the adapter. Whether data may be kept after cancelling is **UNVERIFIED** (it is asked in the email). Tiingo's free plan allows in-memory use only, and its dividends lack pay dates, so R-8.8 would reject them. It is therefore not usable for dividend scenarios without a second pay-date source.

**Synthetic-scenario rules:**
- The generator (`engine/src/roundup_scenarios/`) is seeded and deterministic, with Decimal and integer arithmetic only. Its model and parameters are documented in SCENARIO-MODEL.md.
- Split dates in scenarios are seeded (40–60% through the range), not copied from real events. The real VOO 2013 reverse split and SCHD 2024 forward split are exercised separately, by golden tests on synthetic prices (TEST-STRATEGY.md §0).
- The UI never shows a scenario next to a real ticker or logo, and never calls one a forecast.

**Why not use the real data anyway "since it's invite-only"?** The quoted terms make no exception for private audiences. The cost of being wrong is a terms violation attached to a portfolio piece. A labelled sample teaches the same mechanics: timing, dividends, splits and the threshold rule.

## 6. Adapter design (provider is replaceable)

```
roundup_engine/          # this stage: pure library, no I/O
  market.py              # MarketSeries: calendar, closes, dividends, splits + validation
roundup_data/            # data stage (not built yet)
  ports.py               # MarketDataSource protocol (no provider names)
  adapters/sample.py     # synthetic generator (demo mode)
  adapters/eodhd.py      # local real mode
  checks.py              # data-quality checks (TEST-STRATEGY §5)
```

```python
class MarketDataSource(Protocol):
    name: str
    kind: Literal["sample", "real"]                 # drives the R-12.5 label
    def daily_closes(self, symbol: str, start: date, end: date) -> list[Close]: ...
    def dividends(self, symbol: str, start: date, end: date) -> list[DividendEvent]: ...
    def splits(self, symbol: str, start: date, end: date) -> list[SplitEvent]: ...
    def calendar(self, start: date, end: date) -> list[date]: ...   # calendar-open days
    def capabilities(self) -> Capabilities: ...     # has_pay_date, raw_dividends, may_store, may_display
```

Rules:
- Adapters parse numbers from **strings** into Decimal (R-0.5) and convert dividends to the raw basis (EODHD: `unadjustedValue`), or raise.
- The engine never imports an adapter. It receives a `MarketSeries` object.
- `capabilities().may_store` and `may_display` are set from the licence as we read it. The app refuses to persist or show data whose flags are false. Every flag starts **false** for real providers until written permission arrives.
- Swapping providers = new adapter + contract tests on recorded **sample-shaped** fixtures. Real responses are not recorded into the repo unless the licence allows it.

## 7. Draft emails to providers

Drafts (not sent) are in [drafts/provider-emails.md](drafts/provider-emails.md). The owner will send them.

## 8. Verification gaps

- Coverage of VOO and SCHD at either provider: UNVERIFIED until we hold a key.
- Tiingo's $250 redistribution price: UNVERIFIED (not needed for the demo).
- Whether EODHD personal-plan data may be kept after cancelling: UNVERIFIED.
- Whether "simulation results without price tables" counts as display or redistribution under each provider's terms: UNVERIFIED (the subject of the emails).
- FMP field names, Alpha Vantage's adjustment method, Twelve Data's details: UNVERIFIED (not needed).
- The new VTI index name: UNVERIFIED (VTI is no longer a v1 fund).
