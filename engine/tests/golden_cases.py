"""Golden scenarios with hand-computed expectations.

Every expected value below was worked out by hand from FINANCE-RULES.md before the
engine existed. Prices are deliberately round so each number can be checked on paper.
All market data is synthetic: no real prices appear anywhere in this repository.

Conventions in the January 2024 fixtures: calendar = weekdays 2024-01-02..2024-02-29,
closed 2024-01-15 and 2024-02-19 (holidays).
"""

from builders import closes, div, repeat, scenario, split, tx, weekdays

JAN = weekdays("2024-01-02", "2024-02-29", closed=("2024-01-15", "2024-02-19"))
FLAT50 = closes(JAN, [("2024-01-02", "50.00")])

# Dividend path: 10.00 until 2024-01-09, then 9.60 (the ex-dividend drop).
DIV_PATH = [("2024-01-02", "10.00"), ("2024-01-10", "9.60")]
# Ten purchases of $1.50 on Mon 2024-01-08: round-ups total $5.00, bought Tue 01-09 at 10.00 -> 0.5 sh.
TEN_HALVES = repeat("2024-01-08", "1.50", 10)

CASES = []


def case(s, **expect):
    CASES.append({"scenario": s, "expect": expect})


# ---------------------------------------------------------------- round-ups and timing
case(scenario("G-11", JAN, FLAT50, [tx("2024-01-03", "4.37")], "next_session", "2024-01-02", "2024-01-31",
              description="Wed purchase 4.37 -> 0.63 bought Thu close", covers=["R-2.1", "R-5.1", "R-9.1"]),
     summary={"contributed": "0.63", "roundup_buys": "1", "shares": "0.012600", "ending_value": "0.63",
              "gain": "0.00", "gain_pct": "0.00", "as_of": "2024-01-31", "uninvested_cash": "0.00"},
     buys=[{"date": "2024-01-04", "kind": "roundup", "cash": "0.63", "price": "50.00", "shares": "0.012600",
            "delayed_by_data_gap": "false"}])

case(scenario("G-12", JAN, FLAT50, [tx("2024-01-12", "4.37")], "next_session", "2024-01-02", "2024-01-31",
              description="Fri purchase; Mon is a holiday -> Tue", covers=["R-5.1", "R-5.6"]),
     buys=[{"date": "2024-01-16", "cash": "0.63"}])

case(scenario("G-13", JAN, FLAT50, [tx("2024-01-06", "4.37")], "next_session", "2024-01-02", "2024-01-31",
              description="Saturday purchase -> Monday", covers=["R-5.1"]),
     buys=[{"date": "2024-01-08", "cash": "0.63"}])

case(scenario("G-02", JAN, FLAT50, [tx("2024-01-03", "4.00")], "next_session", "2024-01-02", "2024-01-31",
              description="Whole-dollar purchase rounds up $0; no buy; gain % n/a", covers=["R-2.2", "R-5.1", "R-13.1"]),
     summary={"contributed": "0.00", "roundup_buys": "0", "ending_value": "0.00", "gain": "0.00", "gain_pct": "n/a"},
     buys=[], transactions_used="1", transactions_ignored="0")

case(scenario("G-15", JAN, FLAT50,
              [tx("2024-01-02", "4.01"), tx("2024-01-03", "4.01"), tx("2024-01-04", "4.01"), tx("2024-01-05", "4.01"),
               tx("2024-01-08", "4.01"), tx("2024-01-08", "3.90")],
              "threshold", "2024-01-02", "2024-01-31",
              description="0.99 x5 then 0.10 on the same day crosses $5 -> batch 5.05", covers=["R-5.2"]),
     summary={"contributed": "5.05", "roundup_buys": "1", "shares": "0.101000", "ending_value": "5.05",
              "uninvested_cash": "0.00"},
     buys=[{"date": "2024-01-09", "cash": "5.05", "shares": "0.101000"}])

case(scenario("G-16c", JAN, FLAT50,
              repeat("2024-01-08", "5.20", 2) + repeat("2024-01-09", "5.20", 2) + repeat("2024-01-10", "5.20", 2)
              + [tx("2024-01-12", "2.70"), tx("2024-01-12", "3.10"), tx("2024-01-13", "1.60")],
              "threshold", "2024-01-02", "2024-01-31",
              description="4.80 accumulated, Fri adds 0.30+0.90 -> batch 6.00 (excess not carried); Sat 0.40 starts next batch",
              covers=["R-5.2", "R-5.3", "R-5.4"]),
     summary={"contributed": "6.40", "roundup_buys": "1", "shares": "0.120000", "holdings_value": "6.00",
              "uninvested_cash": "0.40", "ending_value": "6.40"},
     buys=[{"date": "2024-01-16", "cash": "6.00"}])

case(scenario("G-32-threshold-same-day", JAN, FLAT50,
              repeat("2024-01-05", "1.50", 10) + repeat("2024-01-06", "1.50", 10),
              "threshold", "2024-01-02", "2024-01-31",
              description="Batches cut off Fri and Sat both execute Mon as two buys", covers=["R-5.1", "R-5.2"]),
     summary={"roundup_buys": "2", "contributed": "10.00", "ending_value": "10.00"},
     buys=[{"date": "2024-01-08", "cash": "5.00"}, {"date": "2024-01-08", "cash": "5.00"}])

case(scenario("G-14", JAN, FLAT50,
              [tx(f"2024-01-{d:02d}", "1.50") for d in range(8, 16)],
              "weekly", "2024-01-02", "2024-01-31",
              description="Mon-Sun week incl. Sunday -> one buy Tue (Mon holiday); Mon 01-15 belongs to next week",
              covers=["R-5.2"]),
     summary={"roundup_buys": "2", "contributed": "4.00", "ending_value": "4.00"},
     buys=[{"date": "2024-01-16", "cash": "3.50"}, {"date": "2024-01-22", "cash": "0.50"}])

case(scenario("G-monthly", JAN, FLAT50,
              [tx("2024-01-10", "4.37"), tx("2024-01-31", "2.25"), tx("2024-02-05", "1.10")],
              "monthly", "2024-01-02", "2024-02-29",
              description="Jan batch bought Feb 1; Feb batch cut-off Feb 29 has no session in window -> cash",
              covers=["R-5.2", "R-5.4"]),
     summary={"roundup_buys": "1", "contributed": "2.28", "uninvested_cash": "0.90", "ending_value": "2.28"},
     buys=[{"date": "2024-02-01", "cash": "1.38"}])

case(scenario("G-16", JAN, FLAT50, [tx("2024-01-30", "3.75"), tx("2024-01-31", "4.37")], "next_session",
              "2024-01-02", "2024-01-31",
              description="Purchase on the end date stays cash; day-before purchase executes on end date",
              covers=["R-5.4"]),
     summary={"roundup_buys": "1", "contributed": "0.88", "uninvested_cash": "0.63", "ending_value": "0.88"},
     buys=[{"date": "2024-01-31", "cash": "0.25"}])

# ---------------------------------------------------------------- data gaps and window
case(scenario("G-17", JAN, closes(JAN, [("2024-01-02", "50.00")], missing=("2024-01-04",)),
              [tx("2024-01-03", "4.37")], "next_session", "2024-01-02", "2024-01-31",
              description="Missing close Thu -> buy Fri, flagged; Thu valued at carried close",
              covers=["R-6.2", "R-6.4", "R-13.2"]),
     buys=[{"date": "2024-01-05", "delayed_by_data_gap": "true"}],
     series={"2024-01-04": ("0.63", "true"), "2024-01-05": ("0.63", "false")})

case(scenario("G-18", JAN, closes(JAN, [("2024-01-02", "50.00")],
                                  missing=("2024-01-22", "2024-01-23", "2024-01-24", "2024-01-25")),
              [tx("2024-01-03", "4.37")], "next_session", "2024-01-02", "2024-01-31",
              description="4 consecutive missing closes -> run fails", covers=["R-6.3"]),
     status="error", error_code="GAP_TOO_LONG")

case(scenario("G-18-ok", JAN, closes(JAN, [("2024-01-02", "50.00")],
                                     missing=("2024-01-22", "2024-01-23", "2024-01-24")),
              [tx("2024-01-03", "4.37")], "next_session", "2024-01-02", "2024-01-31",
              description="3 consecutive missing closes is allowed", covers=["R-6.3"]),
     status="ok", summary={"ending_value": "0.63"})

_EARLY_END = {k: v for k, v in FLAT50.items() if k <= "2024-02-27"}
case(scenario("G-18c", JAN, _EARLY_END, [tx("2024-01-03", "4.37")], "next_session", "2024-01-02", "2024-02-27",
              description="Calendar days after the last close are 'no data yet', not gaps", covers=["R-6.5"]),
     status="ok", summary={"as_of": "2024-02-27"})

case(scenario("G-18d", JAN, _EARLY_END, [tx("2024-01-03", "4.37")], "next_session", "2024-01-02", "2024-02-28",
              description="End after the last close -> rejected", covers=["R-12.1"]),
     status="error", error_code="WINDOW_OUTSIDE_DATA")

case(scenario("G-28", JAN, FLAT50, [tx("2024-01-03", "4.37")], "next_session", "2023-12-29", "2024-01-31",
              description="Start before the first close -> rejected", covers=["R-12.1"]),
     status="error", error_code="WINDOW_OUTSIDE_DATA")

# ---------------------------------------------------------------- transactions (review finding H5)
case(scenario("G-05-H5", JAN, FLAT50, [
    tx("2024-01-03", "20.00", direction="credit", desc="PAYROLL"),
    tx("2024-01-03", "3.50", status="pending", desc="DELI"),
    tx("2024-01-03", "512.37", desc="PAYMENT TO CHASE CARD"),
    tx("2024-01-03", "40.00", desc="ATM WITHDRAWAL"),
    tx("2024-01-03", "4.37", desc="COFFEE"),
    tx("2024-01-03", "25.50", desc="LATE FEE"),
    tx("2024-01-03", "7.25", type_="Transfer", desc="MOVE MONEY"),
    tx("2024-01-03", "3.30", desc="ZELLE TO SAM"),
    tx("2024-01-03", "9.99", desc="CASH APP*FRIEND"),
    tx("2024-01-03", "12.40", desc="VENMO"),
    tx("2024-01-03", "6.10", status="cancelled", desc="BOOKSHOP"),
], "next_session", "2024-01-02", "2024-01-31",
    description="Card payments, transfers, ATM, P2P, fees, credits, pending and cancelled rows never round up; COFFEE does",
    covers=["R-1.4", "R-1.8", "R-3.2"]),
     summary={"contributed": "0.63", "roundup_buys": "1"}, transactions_used="1", transactions_ignored="10")

case(scenario("G-06", JAN, FLAT50, [tx("2024-01-08", "4.37"), tx("2024-01-10", "4.37", direction="credit", desc="REFUND")],
              "next_session", "2024-01-02", "2024-01-31",
              description="A refund after the round-up was invested reverses nothing", covers=["R-3.1", "R-1.8"]),
     summary={"contributed": "0.63", "ending_value": "0.63"}, transactions_used="1", transactions_ignored="1")

case(scenario("G-04", JAN, FLAT50, [tx("2024-01-03", "4.375"), tx("2024-01-03", "abc"), tx("2024-01-03", "-3.00"),
                                   tx("2024-01-03", "4.37")], "next_session", "2024-01-02", "2024-01-31",
              description="Invalid amounts are rejected rows, not rounded", covers=["R-0.1"]),
     summary={"contributed": "0.63"}, transactions_used="1", transactions_ignored="3")

case(scenario("G-1.6", JAN, FLAT50, [tx("2023-12-29", "4.37"), tx("2024-01-03", "4.37"), tx("2024-02-05", "4.37")],
              "next_session", "2024-01-02", "2024-01-31",
              description="Rows outside the window are excluded", covers=["R-1.6"]),
     summary={"contributed": "0.63"}, transactions_used="1", transactions_ignored="2")

# ---------------------------------------------------------------- dividends
DIV = closes(JAN, DIV_PATH)
case(scenario("G-21", JAN, DIV, TEN_HALVES, "next_session", "2024-01-02", "2024-01-31",
              dividends=[div("2024-01-10", "2024-01-12", "0.40")],
              description="Bought at close of ex-1 -> entitled; reinvested at pay-date close; receivable fills the ex-date drop",
              covers=["R-8.1", "R-8.2", "R-8.3", "R-8.4", "R-8.5"]),
     summary={"contributed": "5.00", "dividends_earned": "0.20", "dividends_paid": "0.20", "dividend_buys": "1",
              "roundup_buys": "1", "shares": "0.520833", "ending_value": "5.00", "receivables": "0.00",
              "uninvested_cash": "0.00", "gain": "0.00"},
     buys=[{"date": "2024-01-09", "kind": "roundup", "cash": "5.00", "shares": "0.500000"},
           {"date": "2024-01-12", "kind": "dividend", "cash": "0.20", "price": "9.60", "shares": "0.020833"}],
     series={"2024-01-09": ("5.00", "false"), "2024-01-10": ("5.00", "false"), "2024-01-11": ("5.00", "false")})

case(scenario("G-22", JAN, DIV, TEN_HALVES, "next_session", "2024-01-02", "2024-01-31",
              dividends=[div("2024-01-09", "2024-01-12", "0.40")],
              description="Bought at the close of the ex-date -> not entitled; zero-share dividend not counted",
              covers=["R-8.2", "R-8.3"]),
     summary={"dividends_earned": "0.00", "dividend_buys": "0", "shares": "0.500000", "ending_value": "4.80",
              "gain": "-0.20", "gain_pct": "-4.00"})

case(scenario("G-24", JAN, DIV, TEN_HALVES, "next_session", "2024-01-02", "2024-01-31", reinvest=False,
              dividends=[div("2024-01-10", "2024-01-12", "0.40")],
              description="Reinvest off: dividend becomes cash at 0%", covers=["R-8.6"]),
     summary={"dividend_buys": "0", "shares": "0.500000", "uninvested_cash": "0.20", "ending_value": "5.00",
              "dividends_paid": "0.20"})

case(scenario("G-32", JAN, DIV, TEN_HALVES, "next_session", "2024-01-02", "2024-01-11",
              dividends=[div("2024-01-10", "2024-01-12", "0.40")],
              description="Ex before end, pay after end: earned not paid; receivable in ending value",
              covers=["R-8.4", "R-13.1"]),
     summary={"dividends_earned": "0.20", "dividends_paid": "0.00", "receivables": "0.20", "holdings_value": "4.80",
              "ending_value": "5.00", "dividend_buys": "0"})

case(scenario("G-32b", JAN, DIV, TEN_HALVES, "next_session", "2024-01-02", "2024-02-03",
              dividends=[div("2024-01-10", "2024-02-03", "0.40")],
              description="Paid on Sat end date; reinvestment session is after end -> stays cash",
              covers=["R-8.5", "R-13.1"]),
     summary={"dividends_paid": "0.20", "uninvested_cash": "0.20", "receivables": "0.00", "ending_value": "5.00",
              "dividend_buys": "0", "as_of": "2024-02-02"})

case(scenario("G-31-paygap", JAN, closes(JAN, DIV_PATH, missing=("2024-01-12",)), TEN_HALVES, "next_session",
              "2024-01-02", "2024-01-31", dividends=[div("2024-01-10", "2024-01-12", "0.40")],
              description="Pay date is a data gap -> reinvest next session (Tue, Mon holiday), flagged",
              covers=["R-8.5", "R-6.2"]),
     summary={"shares": "0.520833", "ending_value": "5.00"},
     buys=[{"date": "2024-01-09"}, {"date": "2024-01-16", "kind": "dividend", "delayed_by_data_gap": "true"}])

# ---------------------------------------------------------------- splits
SPLIT3 = closes(JAN, [("2024-01-02", "30.00"), ("2024-01-17", "10.00")])
TWELVE_HALVES = repeat("2024-01-08", "1.50", 12)
case(scenario("G-25", JAN, SPLIT3, TWELVE_HALVES, "next_session", "2024-01-02", "2024-01-31",
              splits=[split("2024-01-17", "3")], dividends=[div("2024-01-24", "2024-01-26", "0.10")],
              description="3-for-1 split: shares x3, value continuous; later dividend on raw (post-split) basis",
              covers=["R-7.4", "R-7.5", "R-8.1"]),
     summary={"shares": "0.606000", "ending_value": "6.06", "dividends_earned": "0.06", "gain": "0.06",
              "gain_pct": "1.00"},
     series={"2024-01-16": ("6.00", "false"), "2024-01-17": ("6.00", "false")})

# H1: missing price on a split or ex-dividend day
case(scenario("G-H1-div", JAN, closes(JAN, DIV_PATH, missing=("2024-01-10",)), TEN_HALVES, "next_session",
              "2024-01-02", "2024-01-31", dividends=[div("2024-01-10", "2024-01-12", "0.40")],
              description="Review H1: data gap on an ex-dividend date fails the run", covers=["R-6.3"]),
     status="error", error_code="GAP_ON_EVENT")
case(scenario("G-H1-split", JAN, closes(JAN, [("2024-01-02", "30.00"), ("2024-01-17", "10.00")], missing=("2024-01-17",)),
              TWELVE_HALVES, "next_session", "2024-01-02", "2024-01-31", splits=[split("2024-01-17", "3")],
              description="Review H1: data gap on a split ex-date fails the run", covers=["R-6.3"]),
     status="error", error_code="GAP_ON_EVENT")
case(scenario("G-H1-outside", JAN, closes(JAN, DIV_PATH, missing=("2024-01-10",)), [tx("2024-01-22", "4.37")],
              "next_session", "2024-01-16", "2024-01-31", dividends=[div("2024-01-10", "2024-01-12", "0.40")],
              description="Gap on an event ex-date fails even outside the window (whole-input check)",
              covers=["R-6.3"]),
     status="error", error_code="GAP_ON_EVENT")

# H2: shares held for a dividend are fixed at the ex-date, not the pay date
H2_PATH = [("2024-01-02", "1.00"), ("2024-01-10", "0.95"), ("2024-01-17", "0.475")]
case(scenario("G-H2", JAN, closes(JAN, H2_PATH), repeat("2024-01-08", "1.50", 20), "next_session",
              "2024-01-02", "2024-01-31", splits=[split("2024-01-17", "2")],
              dividends=[div("2024-01-10", "2024-01-24", "0.05")],
              description="Review H2: 10 sh at ex-date, 2-for-1 split before pay -> dividend 0.50 (not 1.00)",
              covers=["R-8.3"]),
     summary={"dividends_earned": "0.50", "dividends_paid": "0.50", "shares": "21.052632", "ending_value": "10.00",
              "gain": "0.00"},
     buys=[{"date": "2024-01-09", "shares": "10.000000"},
           {"date": "2024-01-24", "kind": "dividend", "cash": "0.50", "price": "0.475", "shares": "1.052632"}])

# H3: split and dividend on the same ex-date
case(scenario("G-H3", JAN, closes(JAN, [("2024-01-02", "10.00"), ("2024-01-17", "4.80")]),
              repeat("2024-01-08", "1.50", 20), "next_session", "2024-01-02", "2024-01-31",
              splits=[split("2024-01-17", "2")], dividends=[div("2024-01-17", "2024-01-19", "0.20")],
              description="Review H3: 1 sh, 2-for-1 split and 0.20 post-split dividend same day -> 0.40 (not 0.20)",
              covers=["R-8.1", "R-8.2"]),
     summary={"dividends_earned": "0.40", "shares": "2.083333", "ending_value": "10.00",
              "deepest_dip": None})   # value equals added exactly (cross-check finding: no 1e-27 "dip")

# H4: split-adjusted close combined with split events
case(scenario("G-H4", JAN, closes(JAN, [("2024-01-02", "10.00")]), TWELVE_HALVES, "next_session",
              "2024-01-02", "2024-01-31", splits=[split("2024-01-17", "3")],
              description="Review H4: series continuous across a 3-for-1 split is split-adjusted -> rejected",
              covers=["R-7.5"]),
     status="error", error_code="SPLIT_ADJUSTED_SERIES")

# ---------------------------------------------------------------- other data errors
case(scenario("G-26e", JAN, DIV, TEN_HALVES, "next_session", "2024-01-02", "2024-01-31",
              dividends=[div("2024-01-12", "2024-01-10", "0.40")],
              description="Ex-date after pay date (due-bill case) blocks", covers=["R-8.7"]),
     status="error", error_code="EX_AFTER_PAY")
case(scenario("G-8.8", JAN, DIV, TEN_HALVES, "next_session", "2024-01-02", "2024-01-31",
              dividends=[div("2024-01-10", None, "0.40")],
              description="Dividend without pay date is rejected", covers=["R-8.8"]),
     status="error", error_code="MISSING_PAY_DATE")
case(scenario("G-6.3c-ex", JAN, DIV, TEN_HALVES, "next_session", "2024-01-02", "2024-01-31",
              dividends=[div("2024-01-13", "2024-01-16", "0.40")],
              description="Ex-date on a Saturday", covers=["R-6.3"]),
     status="error", error_code="EVENT_NOT_CALENDAR_DAY")
case(scenario("G-6.3c-close", JAN, {**FLAT50, "2024-01-15": "50.00"}, [tx("2024-01-03", "4.37")], "next_session",
              "2024-01-02", "2024-01-31", description="Close on a holiday", covers=["R-6.3"]),
     status="error", error_code="CLOSE_ON_CLOSED_DAY")

# ---------------------------------------------------------------- real-event-shaped (synthetic prices)
# VOO: "Adjusted to reflect a 1-for-2 reverse share split as of the close of business on October 24, 2013"
# (Vanguard 485BPOS, SEC). First post-split session taken as 2013-10-25 (inferred; confirm from real data).
OCT13 = weekdays("2013-10-14", "2013-11-08")
VOO_RAW = closes(OCT13, [("2013-10-14", "80.00"), ("2013-10-25", "160.00")])
VOO_TX = repeat("2013-10-15", "3.40", 10) + repeat("2013-10-28", "3.40", 10)
case(scenario("G-VOO-2013", OCT13, VOO_RAW, VOO_TX, "threshold", "2013-10-14", "2013-11-08",
              splits=[split("2013-10-25", "0.5")],
              description="VOO-shaped 1-for-2 reverse split (sample prices): shares halve, value continuous",
              covers=["R-7.4", "R-7.5"]),
     summary={"contributed": "12.00", "roundup_buys": "2", "shares": "0.075000", "ending_value": "12.00"},
     buys=[{"date": "2013-10-16", "cash": "6.00", "price": "80.00", "shares": "0.075000"},
           {"date": "2013-10-29", "cash": "6.00", "price": "160.00", "shares": "0.037500"}],
     series={"2013-10-24": ("6.00", "false"), "2013-10-25": ("6.00", "false")})
case(scenario("G-VOO-2013-adjusted", OCT13, closes(OCT13, [("2013-10-14", "160.00")]), VOO_TX, "threshold",
              "2013-10-14", "2013-11-08", splits=[split("2013-10-25", "0.5")],
              description="Same split on a split-adjusted series -> rejected", covers=["R-7.5"]),
     status="error", error_code="SPLIT_ADJUSTED_SERIES")

# SCHD: "Shares will begin trading at their post-split price on October 11, 2024" (Schwab press release).
# Synthetic dividend straddling the split exercises review finding H2 on real dates.
OCT24 = weekdays("2024-10-01", "2024-10-31")
SCHD_RAW = closes(OCT24, [("2024-10-01", "81.00"), ("2024-10-07", "80.25"), ("2024-10-11", "26.75")])
case(scenario("G-SCHD-2024", OCT24, SCHD_RAW, repeat("2024-10-02", "4.60", 15), "threshold",
              "2024-10-01", "2024-10-31", splits=[split("2024-10-11", "3")],
              dividends=[div("2024-10-07", "2024-10-15", "0.75")],
              description="SCHD-shaped 3-for-1 split (sample prices) with a dividend whose ex-date is before the split "
                          "and pay date after it",
              covers=["R-7.4", "R-7.5", "R-8.3"]),
     summary={"contributed": "6.00", "dividends_earned": "0.06", "shares": "0.224299", "ending_value": "6.00",
              "gain": "0.00", "deepest_dip": None},
     buys=[{"date": "2024-10-03", "cash": "6.00", "price": "81.00", "shares": "0.074074"},
           {"date": "2024-10-15", "kind": "dividend", "cash": "0.06", "price": "26.75", "shares": "0.002077"}])

# ---------------------------------------------------------------- stage 5: cash split and deepest dip (hand-worked)
# G-24 again: reinvest off. Round-ups all bought (0.00 waiting); the 0.20 dividend is kept as cash.
# Value: Jan 9 = 0.5 x 10.00 = 5.00 vs added 5.00 (not below). Jan 10 onward: 0.5 x 9.60 + 0.20 = 5.00 -> never below.
case(scenario("G-40-split-off", JAN, DIV, TEN_HALVES, "next_session", "2024-01-02", "2024-01-31", reinvest=False,
              dividends=[div("2024-01-10", "2024-01-12", "0.40")],
              description="Cash split: dividends kept as cash 0.20, round-ups waiting 0.00; never below added",
              covers=["R-13.1"]),
     summary={"uninvested_cash": "0.20", "roundups_waiting": "0.00", "dividends_as_cash": "0.20", "deepest_dip": None})

# G-16c again: Sat round-up 0.40 never reaches $5 -> waiting 0.40; no dividends. Price flat 50 -> value = added always.
case(scenario("G-41-split-waiting", JAN, FLAT50,
              repeat("2024-01-08", "5.20", 2) + repeat("2024-01-09", "5.20", 2) + repeat("2024-01-10", "5.20", 2)
              + [tx("2024-01-12", "2.70"), tx("2024-01-12", "3.10"), tx("2024-01-13", "1.60")],
              "threshold", "2024-01-02", "2024-01-31",
              description="Cash split: 0.40 of round-ups waiting, no dividend cash", covers=["R-13.1"]),
     summary={"uninvested_cash": "0.40", "roundups_waiting": "0.40", "dividends_as_cash": "0.00", "deepest_dip": None})

# G-22 again: 0.5 sh bought at 10.00 on Jan 9 (not entitled to the Jan 9 dividend); price 9.60 from Jan 10.
# Jan 10..Jan 31: value 4.80 vs added 5.00 -> below by 0.20 every day; earliest such day is Jan 10.
case(scenario("G-42-dip", JAN, DIV, TEN_HALVES, "next_session", "2024-01-02", "2024-01-31",
              dividends=[div("2024-01-09", "2024-01-12", "0.40")],
              description="Deepest dip: value 4.80 vs added 5.00 from Jan 10; ties go to the earliest date",
              covers=["R-13.1"]),
     summary={"deepest_dip": {"date": "2024-01-10", "value": "4.80", "added": "5.00", "below_by": "0.20"}})

# Dip with a recovery and a carried gap day: flat 50, buy 0.63 Thu Jan 4; price 40 on Jan 8-9 (value 0.504 vs 0.63);
# Jan 9 is missing -> carried at 40; price back to 50 from Jan 10. Deepest = Jan 8 (earliest of the tie), below by 0.126.
DIP = closes(JAN, [("2024-01-02", "50.00"), ("2024-01-08", "40.00"), ("2024-01-10", "50.00")], missing=("2024-01-09",))
case(scenario("G-43-dip-recovers", JAN, DIP, [tx("2024-01-03", "4.37")], "next_session", "2024-01-02", "2024-01-31",
              description="Dip then recovery; carried gap day ties, earliest wins; exact value shown to the cent",
              covers=["R-13.1", "R-6.4"]),
     summary={"ending_value": "0.63",
              "deepest_dip": {"date": "2024-01-08", "value": "0.50", "added": "0.63", "below_by": "0.13"}})

# Reviewer finding H1 (stage 5): a window with no trading day used to return an empty series and an as_of before start.
case(scenario("G-44-no-session", JAN, FLAT50, [tx("2024-01-06", "4.37")], "next_session", "2024-01-06", "2024-01-07",
              description="Window covers only a weekend: no trading day inside it -> rejected", covers=["R-12.1"]),
     status="error", error_code="WINDOW_OUTSIDE_DATA")
case(scenario("G-45-holiday-only", JAN, FLAT50, [tx("2024-01-15", "4.37")], "next_session", "2024-01-15", "2024-01-15",
              description="Window is a single market holiday -> rejected", covers=["R-12.1"]),
     status="error", error_code="WINDOW_OUTSIDE_DATA")
case(scenario("G-46-single-session", JAN, FLAT50, [tx("2024-01-16", "4.37")], "next_session", "2024-01-16", "2024-01-16",
              description="Window of one trading day is valid (purchase that day stays cash)", covers=["R-12.1", "R-5.4"]),
     summary={"as_of": "2024-01-16", "uninvested_cash": "0.63", "roundup_buys": "0"})
