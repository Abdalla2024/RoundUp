# Hand-calculated scenarios (for owner verification)

Five scenarios worked by hand from FINANCE-RULES.md. Each one is also a golden test (ID in brackets), so the engine and the independent cross-check both reproduce these numbers. **Your check is the third, independent one.**

How to use: paste each "Working" table into a spreadsheet. Column D holds the formula; check that it gives column E. All prices are synthetic.

- **Calendar:** weekdays only. In HC-1 to HC-3 (Jan 2024), 2024-01-15 is a holiday.
- **Execution rule:** a batch is bought at the close of the first trading day strictly after its cut-off date (R-5.1).
- **Display rounding:** money to the cent, shares to 6 places, both half-even (R-0.4).

---

## HC-1: $5 threshold, excess not carried, Saturday leftover [G-16c]

**Inputs:** strategy `threshold` ($5.00); price **$50.00** every day; window 2024-01-02 → 2024-01-31.

| Date | Purchases | Round-up each | Day total |
|---|---|---|---|
| Mon 01-08 | 2 × $5.20 | $0.80 | $1.60 |
| Tue 01-09 | 2 × $5.20 | $0.80 | $1.60 |
| Wed 01-10 | 2 × $5.20 | $0.80 | $1.60 |
| Fri 01-12 | $2.70, $3.10 | $0.30, $0.90 | $1.20 |
| Sat 01-13 | $1.60 | $0.40 | $0.40 |

**Working:**

| A Step | B Date | C What | D Formula | E Result |
|---|---|---|---|---|
| 1 | 01-10 | Running total after Wed | `=1.60+1.60+1.60` | 4.80 (below 5.00, no batch) |
| 2 | 01-12 | Fri adds both purchases (all purchases on the crossing date count) | `=4.80+1.20` | 6.00 ≥ 5.00, so cut-off = 01-12 |
| 3 | 01-16 | First trading day after Fri 01-12 (Mon 01-15 is a holiday) | — | Tue 01-16 |
| 4 | 01-16 | Shares bought | `=6.00/50` | 0.120000 |
| 5 | 01-13 | Sat round-up starts a new batch; it never reaches $5 | — | $0.40 stays cash |
| 6 | 01-31 | Holdings value | `=0.12*50` | 6.00 |
| 7 | 01-31 | Ending value = holdings + cash | `=6.00+0.40` | 6.40 |

**Expected:** contributed **$6.40** · round-up buys **1** · shares **0.120000** · uninvested cash **$0.40** · ending value **$6.40** · gain **$0.00**.

---

## HC-2: dividend earned, receivable, reinvested on pay date [G-21]

**Inputs:** strategy `next_session`; reinvest **on**; window 2024-01-02 → 2024-01-31.
- **Prices:** **$10.00** through 2024-01-09, then **$9.60** from 2024-01-10.
- **Purchases:** ten purchases of $1.50 on Mon 2024-01-08 (round-up $0.50 each).
- **Dividend:** ex-date **2024-01-10**, pay date **2024-01-12**, **$0.40** per share.

**Working:**

| A Step | B Date | C What | D Formula | E Result |
|---|---|---|---|---|
| 1 | 01-08 | Round-ups | `=10*0.50` | 5.00 |
| 2 | 01-09 | Bought at the next trading day's close | `=5.00/10.00` | 0.500000 sh |
| 3 | 01-10 | Entitled shares = held at the close before the ex-date | — | 0.5 |
| 4 | 01-10 | Dividend fixed on the ex-date (receivable) | `=0.5*0.40` | 0.20 |
| 5 | 01-10 | Value on the ex-date = shares × price + receivable | `=0.5*9.60+0.20` | 5.00 (no artificial dip) |
| 6 | 01-12 | Reinvested at the pay-date close | `=0.20/9.60` | 0.020833 sh |
| 7 | 01-31 | Total shares | `=0.5+0.20/9.60` | 0.520833 |
| 8 | 01-31 | Ending value | `=(0.5+0.20/9.60)*9.60` | 5.00 |

**Expected:** contributed **$5.00** · dividends earned **$0.20**, paid **$0.20** · dividend buys **1** · shares **0.520833** · ending value **$5.00** · gain **$0.00** · gain % **0.00**.

The price drop and the dividend cancel out exactly. That is the point of this case: the dividend must be counted once, not twice and not zero times.

---

## HC-3: split between ex-date and pay date (review finding H2) [G-H2]

**Inputs:** strategy `next_session`; reinvest **on**; window 2024-01-02 → 2024-01-31.
- **Prices:** **$1.00** to 01-09; **$0.95** 01-10 to 01-16; **$0.475** from 01-17.
- **Purchases:** twenty purchases of $1.50 on 2024-01-08.
- **Dividend:** ex **2024-01-10**, pay **2024-01-24**, **$0.05** per share.
- **Split:** **2-for-1**, ex-date **2024-01-17**.

**Working:**

| A Step | B Date | C What | D Formula | E Result |
|---|---|---|---|---|
| 1 | 01-08 | Round-ups | `=20*0.50` | 10.00 |
| 2 | 01-09 | Shares bought | `=10.00/1.00` | 10 |
| 3 | 01-10 | Dividend fixed on the ex-date from 10 shares | `=10*0.05` | 0.50 |
| 4 | 01-17 | Split: shares × 2 (the dividend does **not** change) | `=10*2` | 20 |
| 5 | 01-17 | Split check: is the price raw? Undoing the split must make the day's move smaller | `=0.475*2/0.95` vs `=0.95/0.475` | 1 < 2 ✓ raw |
| 6 | 01-24 | Reinvest the $0.50 at the pay-date close | `=0.50/0.475` | 1.052632 sh |
| 7 | 01-31 | Total shares | `=20+0.50/0.475` | 21.052632 |
| 8 | 01-31 | Ending value | `=(20+0.50/0.475)*0.475` | 10.00 |

**Expected:** dividends earned **$0.50** (a wrong engine using pay-date shares would give $1.00) · shares **21.052632** · ending value **$10.00** · gain **$0.00**.

---

## HC-4: VOO-shaped 1-for-2 reverse split (sample prices) [G-VOO-2013]

**Inputs:** strategy `threshold`; window 2013-10-14 → 2013-11-08 (weekdays).
- **Prices:** **$80.00** through 2013-10-24, **$160.00** from 2013-10-25.
- **Split:** ratio **0.5**, ex-date 2013-10-25. Vanguard's filing says the reverse split was "as of the close of business on October 24, 2013", so the first post-split session is taken as Oct 25. This is inferred; confirm it against real data later.
- **Purchases:** ten purchases of $3.40 on Tue 10-15 and ten on Mon 10-28 (round-up $0.60 each).

**Working:**

| A Step | B Date | C What | D Formula | E Result |
|---|---|---|---|---|
| 1 | 10-15 | Round-ups reach $6.00 (≥ $5) | `=10*0.60` | 6.00, cut-off 10-15 |
| 2 | 10-16 | Bought | `=6.00/80` | 0.075000 sh |
| 3 | 10-24 | Value before the split | `=0.075*80` | 6.00 |
| 4 | 10-25 | Reverse split: shares × 0.5 | `=0.075*0.5` | 0.0375 |
| 5 | 10-25 | Value after the split (continuous) | `=0.0375*160` | 6.00 |
| 6 | 10-29 | Second batch bought at the post-split price | `=6.00/160` | 0.037500 sh |
| 7 | 11-08 | Ending value | `=(0.0375+0.0375)*160` | 12.00 |

**Expected:** contributed **$12.00** · round-up buys **2** · shares **0.075000** · ending value **$12.00**.

If the same split is applied to a series that was already split-adjusted ($160 throughout), the engine must **reject** the data (`SPLIT_ADJUSTED_SERIES`), not halve the shares again.

---

## HC-5: SCHD-shaped 3-for-1 split with a dividend straddling it (sample prices) [G-SCHD-2024]

**Inputs:** strategy `threshold`; window 2024-10-01 → 2024-10-31 (weekdays).
- **Prices:** **$81.00** to 10-04; **$80.25** 10-07 to 10-10; **$26.75** from 10-11.
- **Split:** 3-for-1, ex-date **2024-10-11** (Schwab: post-split trading began Oct 11, 2024).
- **Dividend (synthetic):** ex **10-07**, pay **10-15**, **$0.75** per share.
- **Purchases:** fifteen purchases of $4.60 on 10-02 (round-up $0.40 each).

**Working:**

| A Step | B Date | C What | D Formula | E Result |
|---|---|---|---|---|
| 1 | 10-02 | Round-ups | `=15*0.40` | 6.00, cut-off 10-02 |
| 2 | 10-03 | Bought | `=6.00/81` | 0.074074 sh (exactly 2/27) |
| 3 | 10-07 | Dividend fixed on the ex-date | `=(6/81)*0.75` | 0.0556 (exactly 1/18) |
| 4 | 10-11 | Split: shares × 3 | `=(6/81)*3` | 0.222222 (exactly 2/9) |
| 5 | 10-15 | Reinvest at the post-split price | `=(1/18)/26.75` | 0.002077 sh |
| 6 | 10-31 | Total shares | `=2/9+(1/18)/26.75` | 0.224299 (exactly 24/107) |
| 7 | 10-31 | Ending value | `=(2/9+(1/18)/26.75)*26.75` | 6.00 |

**Expected:** contributed **$6.00** · dividends earned **$0.06** (exact $0.0556; a wrong engine using post-split shares would give $0.17) · shares **0.224299** · ending value **$6.00** · gain **$0.00**.

---

### What to send back

For each case, either "matches" or the step number where your spreadsheet differs. A difference means a rule is ambiguous or a calculation is wrong, and it gets resolved from the rule text (TEST-STRATEGY.md §4).
