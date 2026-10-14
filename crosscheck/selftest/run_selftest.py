"""Self-tests: hand-computed scenarios, error precedence, rounding.  python3 -I run_selftest.py"""
import copy, glob, json, os, sys
from fractions import Fraction as F
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import crosscheck as cc

fails = 0
def check(name, got, want):
    global fails
    if got != want:
        fails += 1
        print("FAIL", name, "\n  got: ", got, "\n  want:", want)
    else:
        print("ok  ", name)

# 1. hand-computed full scenarios
for p in sorted(glob.glob(os.path.join(HERE, "S*.json"))):
    if p.endswith(".expected.json"):
        continue
    sc = json.load(open(p))
    want = json.load(open(p.replace(".json", ".expected.json")))
    got = cc.run(sc)
    for k in want:
        check("%s %s" % (sc["id"], k), got[k], want[k])

# 1b. summary key order must follow the FORMAT.md example
ORDER = ["contributed", "roundup_buys", "dividend_buys", "dividends_earned", "dividends_paid", "shares",
         "holdings_value", "uninvested_cash", "roundups_waiting", "dividends_as_cash", "receivables",
         "ending_value", "gain", "gain_pct", "as_of", "deepest_dip"]
check("summary key order", list(cc.run(json.load(open(os.path.join(HERE, "S5.json"))))["summary"]), ORDER)

# 1c. deepest dip: exact comparison, earliest date on exact ties. Both days display below_by 0.01,
# but day 2 is exactly deeper (0.0144 vs 0.0136), so day 2 must win.
dip_sc = {"id": "dip-exact", "market": {"symbol": "T", "calendar": ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
          "closes": {"2024-01-02": "1.00", "2024-01-03": "1.00", "2024-01-04": "0.966", "2024-01-05": "0.964"},
          "dividends": [], "splits": []},
          "transactions": [{"posted_date": "2024-01-02", "amount": "0.60", "direction": "debit", "status": "posted",
                            "type": "", "description": "x"}],
          "config": {"strategy": "next_session", "start": "2024-01-02", "end": "2024-01-05", "reinvest": "true"}}
check("dip exact beats display tie", cc.run(dip_sc)["summary"]["deepest_dip"],
      {"date": "2024-01-05", "value": "0.39", "added": "0.40", "below_by": "0.01"})

# 2. rounding (half-even on exact fractions)
for x, places, want in [(F(5, 1000), 2, "0.00"), (F(15, 1000), 2, "0.02"), (F(25, 1000), 2, "0.02"),
                        (F(-15, 1000), 2, "-0.02"), (F(-4, 1000), 2, "0.00"), (F(1, 3), 6, "0.333333"),
                        (F(2, 3), 6, "0.666667"), (F(12345, 10), 2, "1234.50"), (F(5, 10**7), 6, "0.000000"),
                        (F(15, 10**7), 6, "0.000002")]:
    check("fmt %s %d" % (x, places), cc.fmt(x, places), want)

# 3. amount parsing and keyword classification
for s, want in [("4.37", 437), ("4", 400), ("4.5", 450), ("1.999", None), ("abc", None), ("-1.00", None), ("", None), ("0.00", 0)]:
    check("amount %r" % s, cc.parse_amount_cents(s), want)
for desc, typ, want in [("COFFEE SHOP", "", False), ("Coffee fee-free", "", True), ("payments inc", "", False),
                        ("CASH APP*BOB", "", True), ("cashapp", "", False), ("atm#123", "", True),
                        ("shop", " Loan ", True), ("shop", "loan payment", False), ("Zelle to Bob", "", True)]:
    check("non-purchase %r/%r" % (desc, typ), cc.is_non_purchase({"description": desc, "type": typ}), want)

# 4. error codes and precedence, built as variants of S4
base = json.load(open(os.path.join(HERE, "S4.json")))
def variant(**kw):
    sc = copy.deepcopy(base)
    for path, val in kw.items():
        obj = sc
        keys = path.split("__")
        for k in keys[:-1]:
            obj = obj[k]
        obj[keys[-1]] = val
    return cc.run(sc)["error_code"]

check("start>end", variant(config__start="2024-02-02", config__end="2024-01-30"), "WINDOW_OUTSIDE_DATA")
check("end after data end", variant(config__end="2024-02-05"), "WINDOW_OUTSIDE_DATA")
check("window beats closed-day close",
      variant(config__start="2024-01-29", market__closes={"2024-01-30": "4", "2024-02-03": "5", "2024-02-02": "5"}),
      "WINDOW_OUTSIDE_DATA")
check("close on closed day", variant(market__closes={"2024-01-30": "4", "2024-02-01": "5", "2024-02-02": "5", "2024-02-03": "5"},
                                     market__dividends=[{"ex_date": "2024-02-01", "pay_date": None, "amount_raw": "1"}]),
      "CLOSE_ON_CLOSED_DAY")
check("event not calendar day", variant(market__splits=[{"ex_date": "2024-01-29", "ratio": "2"}],
                                        market__dividends=[{"ex_date": "2024-02-01", "pay_date": None, "amount_raw": "1"}]),
      "EVENT_NOT_CALENDAR_DAY")
check("missing pay date", variant(market__dividends=[{"ex_date": "2024-02-01", "pay_date": None, "amount_raw": "1"},
                                                     {"ex_date": "2024-02-02", "pay_date": "2024-02-01", "amount_raw": "1"}]),
      "MISSING_PAY_DATE")
check("ex after pay", variant(market__dividends=[{"ex_date": "2024-02-02", "pay_date": "2024-02-01", "amount_raw": "1"}]),
      "EX_AFTER_PAY")
check("ex == pay is fine", variant(market__dividends=[{"ex_date": "2024-02-02", "pay_date": "2024-02-02", "amount_raw": "1"}]),
      None)
# 5.00 -> 5.00 with ratio 2: undoing gives 10 vs 5 (jump 2) vs jump 1 -> adjusted -> reject
check("split-adjusted", variant(market__splits=[{"ex_date": "2024-02-02", "ratio": "2"}]), "SPLIT_ADJUSTED_SERIES")
check("split ratio 1", variant(market__splits=[{"ex_date": "2024-02-02", "ratio": "1"}],
                               market__closes={"2024-01-30": "4.00", "2024-02-01": "5.00", "2024-02-02": "2.50"}),
      "SPLIT_ADJUSTED_SERIES")
check("raw split ok, P skips gap", variant(market__splits=[{"ex_date": "2024-02-01", "ratio": "0.5"}],
                                           market__closes={"2024-01-30": "4.00", "2024-02-01": "8.10", "2024-02-02": "8.00"}),
      None)
check("split on gap day -> GAP_ON_EVENT (beats SPLIT_ADJUSTED)",
      variant(market__splits=[{"ex_date": "2024-01-31", "ratio": "2"}]), "GAP_ON_EVENT")
check("GAP_ON_EVENT beats a split-adjusted split elsewhere",
      variant(market__splits=[{"ex_date": "2024-02-02", "ratio": "2"}],
              market__dividends=[{"ex_date": "2024-01-31", "pay_date": "2024-02-01", "amount_raw": "1"}]),
      "GAP_ON_EVENT")
# Events after the data end (2024-02-02) are ignored entirely: no check applies.
for name, ev_key, ev in [
        ("after data end: null pay date", "dividends", {"ex_date": "2024-02-05", "pay_date": None, "amount_raw": "1"}),
        ("after data end: ex after pay", "dividends", {"ex_date": "2024-02-06", "pay_date": "2024-02-05", "amount_raw": "1"}),
        ("after data end: not a calendar day", "dividends", {"ex_date": "2024-02-03", "pay_date": "2024-02-09", "amount_raw": "1"}),
        ("after data end: calendar day, no close", "splits", {"ex_date": "2024-02-05", "ratio": "2"}),
        ("after data end: ratio 1", "splits", {"ex_date": "2024-02-06", "ratio": "1"})]:
    sc = copy.deepcopy(base)
    sc["market"]["calendar"] = sc["market"]["calendar"] + ["2024-02-05", "2024-02-06"]
    sc["market"][ev_key] = [ev]
    want = json.load(open(os.path.join(HERE, "S4.expected.json")))
    check(name, cc.run(sc), want)
# ... but an event exactly on the data end is checked.
check("on data end: null pay date checked",
      variant(market__dividends=[{"ex_date": "2024-02-02", "pay_date": None, "amount_raw": "1"}]), "MISSING_PAY_DATE")
err = cc.run(dict(copy.deepcopy(base), config=dict(base["config"], start="2024-02-02", end="2024-01-30")))
check("error run: all result fields null",
      [err[k] for k in ("status", "error_code", "summary", "buys", "series", "transactions_used", "transactions_ignored")],
      ["error", "WINDOW_OUTSIDE_DATA", None, None, None, None, None])
check("dividend on gap day", variant(market__dividends=[{"ex_date": "2024-01-31", "pay_date": "2024-02-01", "amount_raw": "1"}]),
      "GAP_ON_EVENT")
check("dividend on gap day before window (anywhere reading)",
      variant(config__start="2024-02-01", market__dividends=[{"ex_date": "2024-01-31", "pay_date": "2024-02-01", "amount_raw": "1"}]),
      "GAP_ON_EVENT")
long_cal = ["2024-01-0%d" % d for d in range(1, 10)]
check("4-day gap in window", variant(market__calendar=long_cal,
      market__closes={"2024-01-01": "1", "2024-01-06": "1", "2024-01-09": "1"},
      config__start="2024-01-01", config__end="2024-01-09"), "GAP_TOO_LONG")
check("3-day gap in window ok", variant(market__calendar=long_cal,
      market__closes={"2024-01-01": "1", "2024-01-05": "1", "2024-01-09": "1"},
      config__start="2024-01-01", config__end="2024-01-09"), None)
check("gap straddling start counts in-window days only", variant(market__calendar=long_cal,
      market__closes={"2024-01-01": "1", "2024-01-06": "1", "2024-01-09": "1"},
      config__start="2024-01-03", config__end="2024-01-09"), None)
check("GAP_ON_EVENT beats GAP_TOO_LONG", variant(market__calendar=long_cal,
      market__closes={"2024-01-01": "1", "2024-01-06": "1", "2024-01-09": "1"},
      market__dividends=[{"ex_date": "2024-01-03", "pay_date": "2024-01-06", "amount_raw": "1"}],
      config__start="2024-01-01", config__end="2024-01-09"), "GAP_ON_EVENT")

# 4b. R-12.1 (stage 5): at least one close must lie inside [start, end] (inclusive).
# Fri 2024-01-12 and Tue 2024-01-16 are sessions; Sat/Sun 13-14 are weekend; Mon 15 is the MLK holiday.
win_mkt = dict(market__calendar=["2024-01-12", "2024-01-16", "2024-01-17"],
               market__closes={"2024-01-12": "4.00", "2024-01-16": "5.00", "2024-01-17": "5.00"})
check("weekend-only window", variant(config__start="2024-01-13", config__end="2024-01-14", **win_mkt),
      "WINDOW_OUTSIDE_DATA")
check("holiday-only window", variant(config__start="2024-01-15", config__end="2024-01-15", **win_mkt),
      "WINDOW_OUTSIDE_DATA")
check("weekend+holiday window", variant(config__start="2024-01-13", config__end="2024-01-15", **win_mkt),
      "WINDOW_OUTSIDE_DATA")
one_day = copy.deepcopy(base)
one_day["market"]["calendar"] = win_mkt["market__calendar"]
one_day["market"]["closes"] = win_mkt["market__closes"]
one_day["config"].update(start="2024-01-16", end="2024-01-16")
one_day["transactions"] = [{"posted_date": "2024-01-16", "amount": "0.60", "direction": "debit",
                            "status": "posted", "type": "", "description": "a"}]
r1 = cc.run(one_day)
check("single-trading-day window ok",
      [r1["status"], r1["error_code"], r1["series"], r1["summary"]["as_of"], r1["summary"]["contributed"],
       r1["summary"]["roundups_waiting"], r1["transactions_used"]],
      ["ok", None, [{"date": "2024-01-16", "value": "0.40", "carried": "false"}], "2024-01-16", "0.40", "0.40", "1"])
check("window touching one close at its end ok",
      variant(config__start="2024-01-13", config__end="2024-01-16", **win_mkt), None)

# 4c. R-1.4a (cautious status rule): only posted/settled/cleared/completed (normalised) or empty/absent count.
def status_tx(status, direction="debit", absent=False):
    t = {"posted_date": "2024-01-16", "amount": "0.60", "direction": direction, "type": "", "description": "a"}
    if not absent:
        t["status"] = status
    return t
S, E = cc.parse_date("2024-01-01"), cc.parse_date("2024-01-31")
for st in ["Settled", "CLEARED", "completed ", "Posted", "  posted", "", None]:
    check("status counted %r" % (st,), cc.classify_transactions([status_tx(st)], S, E), ([(cc.parse_date("2024-01-16"), 60)], 0))
check("status absent counted", cc.classify_transactions([status_tx(None, absent=True)], S, E),
      ([(cc.parse_date("2024-01-16"), 60)], 0))
for st in ["reversed", "declined", "on hold", "ON  HOLD", "unrecognised", "returned", "pending", "cancelled", "Canceled", "void", "VOIDED"]:
    check("status ignored %r" % st, cc.classify_transactions([status_tx(st)], S, E), ([], 1))
check("unrecognised-status credit ignored once", cc.classify_transactions([status_tx("reversed", "credit")], S, E), ([], 1))
check("mixed statuses tally", cc.classify_transactions(
      [status_tx(x) for x in ["settled", "reversed", "on hold", "cleared"]], S, E)[1], 2)

# 5. CLI: multiple files -> mapping id -> result
import subprocess
out = subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(HERE), "crosscheck.py"),
                      os.path.join(HERE, "S1.json"), os.path.join(HERE, "S2.json")], capture_output=True, text=True)
check("CLI multi-file keys", sorted(json.loads(out.stdout)), ["S1", "S2"])

print("\n%d failure(s)" % fails)
sys.exit(1 if fails else 0)
