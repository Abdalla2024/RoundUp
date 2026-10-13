#!/usr/bin/env python3
"""Independent, deliberately naive cross-check of the RoundUp simulation.

Usage:  python3 -I crosscheck.py scenario.json [more.json ...]

All derived arithmetic is exact (fractions.Fraction). Money inputs are integer
cents. Nothing is ever a float. Rounding happens only in fmt() at output time.
See AMBIGUITIES.md for interpretation choices (tagged "AMB-n" below).
"""
import json
import re
import sys
from datetime import date, timedelta
from fractions import Fraction

THRESHOLD_CENTS = 500

# R-1.4 (a): type field values that mark a debit as a non-purchase.
NON_PURCHASE_TYPES = {"payment", "transfer", "atm", "fee", "interest", "loan"}
# R-1.4 (b): whole words in the description.
NON_PURCHASE_WORDS = {"payment", "transfer", "xfer", "atm", "withdrawal", "zelle",
                      "venmo", "autopay", "loan", "fee", "interest"}
# R-1.4 (b): phrase, matched as consecutive whole words (AMB-3).
NON_PURCHASE_PHRASES = [["cash", "app"]]

AMOUNT_RE = re.compile(r"^([0-9]*)(?:\.([0-9]{1,2}))?$")


class DataError(Exception):
    def __init__(self, code):
        Exception.__init__(self, code)
        self.code = code


# ---------------------------------------------------------------- helpers

def parse_date(s):
    return date.fromisoformat(s)


def normalize(s):
    """R-4.5: trimmed, case-folded, internal whitespace collapsed."""
    return " ".join((s or "").casefold().split())


def words(s):
    """R-1.4: a whole word is a run of letters and digits."""
    out = []
    cur = ""
    for ch in s:
        if ch.isalnum():
            cur += ch
        else:
            if cur:
                out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def parse_amount_cents(s):
    """R-0.1: string -> integer cents, or None if invalid (>2 decimals, not a number)."""
    if not isinstance(s, str):
        return None
    m = AMOUNT_RE.match(s)
    if not m:
        return None
    whole, frac = m.group(1), m.group(2)
    if whole == "" and frac is None:
        return None
    if whole == "":
        whole = "0"
    if frac is None:
        frac = ""
    frac = (frac + "00")[:2]
    return int(whole) * 100 + int(frac)


def is_non_purchase(tx):
    t = normalize(tx.get("type", ""))
    if t in NON_PURCHASE_TYPES:
        return True
    ws = words(normalize(tx.get("description", "")))
    for w in ws:
        if w in NON_PURCHASE_WORDS:
            return True
    for phrase in NON_PURCHASE_PHRASES:
        n = len(phrase)
        for i in range(len(ws) - n + 1):
            if ws[i:i + n] == phrase:
                return True
    return False


def fmt(x, places):
    """Round a Fraction half-even to `places` decimals and format it."""
    x = Fraction(x)
    y = x * (10 ** places)
    n = y.numerator // y.denominator          # floor
    rem = y - n
    half = Fraction(1, 2)
    if rem > half or (rem == half and n % 2 == 1):
        n += 1
    sign = "-" if n < 0 else ""
    digits = str(abs(n))
    if places == 0:
        return sign + digits
    digits = digits.rjust(places + 1, "0")
    return sign + digits[:-places] + "." + digits[-places:]


def money(x):
    return fmt(x, 2)


def shares_str(x):
    return fmt(x, 6)


def jump(a, b):
    return max(a / b, b / a)


def sunday_of(d):
    return d + timedelta(days=6 - d.weekday())


def month_end(d):
    if d.month == 12:
        return date(d.year, 12, 31)
    return date(d.year, d.month + 1, 1) - timedelta(days=1)


# ---------------------------------------------------------------- the run

def classify_transactions(txs, start, end):
    used = []      # list of (date, cents)
    ignored = 0
    for tx in txs:
        cents = parse_amount_cents(tx.get("amount"))
        try:
            dt = parse_date(tx.get("posted_date"))
        except (TypeError, ValueError):
            dt = None
        ok = (
            cents is not None                                   # R-0.1
            and cents > 0                                       # R-1.5
            and dt is not None
            and start <= dt <= end                              # R-1.6
            and normalize(tx.get("status")) == "posted"         # R-1.4, R-3.2
            and normalize(tx.get("direction")) == "debit"       # R-1.4, R-1.8
            and not is_non_purchase(tx)                         # R-1.4
        )
        if ok:
            used.append((dt, cents))
        else:
            ignored += 1
    return used, ignored


def validate(calendar, closes, splits, divs, start, end):
    calset = set(calendar)
    # WINDOW_OUTSIDE_DATA (R-12.1)
    if not closes or start > end or start < min(closes) or end > max(closes):
        raise DataError("WINDOW_OUTSIDE_DATA")
    # R-12.1 (stage 5): at least one close inside [start, end], both ends inclusive (AMB-23).
    if not any(start <= d <= end for d in closes):
        raise DataError("WINDOW_OUTSIDE_DATA")
    # R-6.5 / FORMAT.md: events with ex-date after the data end (last close in the
    # input) are "no data yet": ignored entirely, no check of any kind.
    data_end = max(closes)
    splits = [ev for ev in splits if ev["ex"] <= data_end]
    divs = [ev for ev in divs if ev["ex"] <= data_end]
    # CLOSE_ON_CLOSED_DAY (R-6.3(c))
    for d in closes:
        if d not in calset:
            raise DataError("CLOSE_ON_CLOSED_DAY")
    # EVENT_NOT_CALENDAR_DAY (R-6.3(c))
    for ev in splits + divs:
        if ev["ex"] not in calset:
            raise DataError("EVENT_NOT_CALENDAR_DAY")
    # MISSING_PAY_DATE (R-8.8)
    for dv in divs:
        if dv["pay"] is None:
            raise DataError("MISSING_PAY_DATE")
    # EX_AFTER_PAY (R-8.7)
    for dv in divs:
        if dv["ex"] > dv["pay"]:
            raise DataError("EX_AFTER_PAY")
    # GAP_ON_EVENT (R-6.3(b)): whole input (events after the data end were already dropped).
    for ev in splits + divs:
        if ev["ex"] not in closes:
            raise DataError("GAP_ON_EVENT")
    # SPLIT_ADJUSTED_SERIES (R-7.5)
    for sp in splits:
        r = sp["ratio"]
        if r <= 0 or r == 1:
            raise DataError("SPLIT_ADJUSTED_SERIES")
        x = sp["ex"]
        before = [d for d in closes if d < x]       # AMB-5: last *session* before X (skips gaps)
        if not before:
            raise DataError("SPLIT_ADJUSTED_SERIES")
        p = closes[max(before)][0]
        q = closes[x][0]
        if p <= 0 or q <= 0:
            raise DataError("SPLIT_ADJUSTED_SERIES")
        if not (jump(q * r, p) < jump(q, p)):
            raise DataError("SPLIT_ADJUSTED_SERIES")
    # GAP_TOO_LONG (R-6.3(a)): 4+ consecutive calendar-open days without a close,
    # counting only days inside [start, end] (AMB-6).
    run_len = 0
    for d in calendar:
        if d < start or d > end:
            continue
        if d in closes:
            run_len = 0
        else:
            run_len += 1
            if run_len >= 4:
                raise DataError("GAP_TOO_LONG")


def make_batches(strategy, roundups):
    """R-5.2. roundups: list of (date, cents>0). Returns [(cutoff, cents)] in cut-off order."""
    totals = {}
    for dt, c in roundups:
        totals[dt] = totals.get(dt, 0) + c
    days = sorted(totals)
    batches = []
    if strategy == "threshold":
        acc = 0
        for dt in days:
            acc += totals[dt]
            if acc >= THRESHOLD_CENTS:
                batches.append((dt, acc))
                acc = 0
    elif strategy == "next_session":
        for dt in days:
            batches.append((dt, totals[dt]))
    elif strategy in ("weekly", "monthly"):
        key = sunday_of if strategy == "weekly" else month_end
        grouped = {}
        for dt in days:
            c = key(dt)
            grouped[c] = grouped.get(c, 0) + totals[dt]
        for c in sorted(grouped):
            batches.append((c, grouped[c]))
    else:
        raise ValueError("unknown strategy %r" % strategy)
    return [b for b in batches if b[1] > 0]


def run(sc):
    m = sc["market"]
    cfg = sc["config"]
    start = parse_date(cfg["start"])
    end = parse_date(cfg["end"])
    strategy = cfg["strategy"]
    reinvest = cfg["reinvest"] == "true"

    calendar = sorted(set(parse_date(s) for s in m.get("calendar", [])))
    closes = {}
    for k, v in m.get("closes", {}).items():
        closes[parse_date(k)] = (Fraction(v), v)     # (exact value, string as given)
    splits = []
    for i, s in enumerate(m.get("splits", []) or []):
        splits.append({"ex": parse_date(s["ex_date"]), "ratio": Fraction(s["ratio"]), "idx": i})
    divs = []
    for i, dv in enumerate(m.get("dividends", []) or []):
        pay = dv.get("pay_date")
        divs.append({"ex": parse_date(dv["ex_date"]),
                     "pay": parse_date(pay) if pay else None,
                     "amount": Fraction(dv["amount_raw"]), "idx": i})

    used, ignored = classify_transactions(sc.get("transactions", []), start, end)

    try:
        validate(calendar, closes, splits, divs, start, end)
    except DataError as e:
        return {"status": "error", "error_code": e.code, "summary": None, "buys": None,
                "series": None, "transactions_used": None, "transactions_ignored": None}

    roundups = [(dt, (100 - c % 100) % 100) for dt, c in used]           # R-2.1
    roundups = [(dt, r) for dt, r in roundups if r > 0]                  # R-2.2: $0 adds nothing
    contributed_cents = sum(c for _, c in roundups)

    batches = make_batches(strategy, roundups)
    batch_done = [False] * len(batches)

    def first_calendar_day(pred):
        for d in calendar:
            if pred(d):
                return d
        return None

    def delayed_flag(first_day):
        # R-6.2 / R-8.5: flagged when the first calendar-open day is a data gap.
        return first_day is not None and first_day not in closes

    def last_close_on_or_before(d):
        ds = [x for x in closes if x <= d]
        return max(ds) if ds else None

    shares = Fraction(0)
    bought_cents = 0
    fixed = []          # fixed dividend receivables: dicts with ex, pay, cash, idx, reinvested
    buys = []
    series = []
    divs_sorted = sorted(divs, key=lambda x: (x["ex"], x["idx"]))
    splits_sorted = sorted(splits, key=lambda x: (x["ex"], x["idx"]))

    def added_by(day):
        """Round-ups contributed (dated) on or before `day`, exact dollars."""
        return Fraction(sum(c for dt, c in roundups if dt <= day), 100)

    def value_parts(day):
        """(round-ups waiting, dividends as cash, receivables) at the end of `day`."""
        rcash = added_by(day) - Fraction(bought_cents, 100)
        dcash = sum((f["cash"] for f in fixed if f["pay"] <= day and not f["reinvested"]), Fraction(0))
        recv = sum((f["cash"] for f in fixed if f["pay"] > day), Fraction(0))
        return rcash, dcash, recv

    dip = None          # (below_by, day, value, added), exact; strictly larger wins -> earliest on ties

    for day in calendar:
        if day < start or day > end:
            continue
        if day in closes:
            price, price_str = closes[day]
            # R-8.1 (1) splits
            for sp in splits_sorted:
                if sp["ex"] == day:
                    shares = shares * sp["ratio"]
            # R-8.1 (2) dividend entitlements (R-8.2, R-8.3)
            for dv in divs_sorted:
                if dv["ex"] == day and shares > 0:
                    fixed.append({"ex": dv["ex"], "pay": dv["pay"], "cash": shares * dv["amount"],
                                  "idx": dv["idx"], "reinvested": False})
            # R-8.1 (3) buys: round-up batches in cut-off order (R-5.1) ...
            for i, (cut, cents) in enumerate(batches):
                if not batch_done[i] and cut < day:
                    cash = Fraction(cents, 100)
                    bought = cash / price
                    shares += bought
                    bought_cents += cents
                    batch_done[i] = True
                    fd = first_calendar_day(lambda d, cut=cut: d > cut)
                    buys.append({"date": day.isoformat(), "kind": "roundup", "cash": money(cash),
                                 "price": price_str, "shares": shares_str(bought),
                                 "delayed_by_data_gap": "true" if delayed_flag(fd) else "false"})
            # ... then dividend reinvestments in ex-date order (R-8.5)
            if reinvest:
                for f in sorted(fixed, key=lambda x: (x["ex"], x["idx"])):
                    if not f["reinvested"] and f["pay"] <= day:
                        bought = f["cash"] / price
                        shares += bought
                        f["reinvested"] = True
                        fd = first_calendar_day(lambda d, p=f["pay"]: d >= p)
                        buys.append({"date": day.isoformat(), "kind": "dividend",
                                     "cash": money(f["cash"]), "price": price_str,
                                     "shares": shares_str(bought),
                                     "delayed_by_data_gap": "true" if delayed_flag(fd) else "false"})
            carried = False
        else:
            # R-6.4: valuation only, carry the last close forward.
            lc = last_close_on_or_before(day)
            price = closes[lc][0]
            carried = True
        # R-8.1 (4) valuation (R-13.2)
        rcash, dcash, recv = value_parts(day)
        value = shares * price + rcash + dcash + recv
        series.append({"date": day.isoformat(), "value": money(value),
                       "carried": "true" if carried else "false"})
        # Deepest dip (R-13.1, FORMAT.md): largest positive (added - value), exact.
        added = added_by(day)
        below = added - value
        if below > 0 and (dip is None or below > dip[0]):
            dip = (below, day, value, added)

    # R-13.1 summary, as of the end date.
    as_of = last_close_on_or_before(end)
    holdings = shares * closes[as_of][0]
    rcash, dcash, recv = value_parts(end)
    cash = rcash + dcash
    ending = holdings + cash + recv
    contributed = Fraction(contributed_cents, 100)
    gain = ending - contributed
    earned = sum((f["cash"] for f in fixed), Fraction(0))
    paid = sum((f["cash"] for f in fixed if f["pay"] <= end), Fraction(0))
    summary = {
        "contributed": money(contributed),
        "roundup_buys": str(sum(1 for b in buys if b["kind"] == "roundup")),
        "dividend_buys": str(sum(1 for b in buys if b["kind"] == "dividend")),
        "dividends_earned": money(earned),
        "dividends_paid": money(paid),
        "shares": shares_str(shares),
        "holdings_value": money(holdings),
        "uninvested_cash": money(cash),
        "roundups_waiting": money(rcash),
        "dividends_as_cash": money(dcash),
        "receivables": money(recv),
        "ending_value": money(ending),
        "gain": money(gain),
        "gain_pct": "n/a" if contributed == 0 else fmt(gain / contributed * 100, 2),
        "as_of": as_of.isoformat(),
        "deepest_dip": None if dip is None else {
            "date": dip[1].isoformat(), "value": money(dip[2]),
            "added": money(dip[3]), "below_by": money(dip[0])},
    }
    return {"status": "ok", "error_code": None, "summary": summary, "buys": buys,
            "series": series, "transactions_used": str(len(used)),
            "transactions_ignored": str(ignored)}


def main(argv):
    if not argv:
        sys.stderr.write("usage: crosscheck.py scenario.json [more.json ...]\n")
        return 2
    results = {}
    for path in argv:
        with open(path, encoding="utf-8") as fh:
            sc = json.load(fh, parse_float=lambda s: (_ for _ in ()).throw(
                ValueError("float literal in input: " + s)))
        results[sc.get("id", path)] = run(sc)
    if len(argv) == 1:
        out = next(iter(results.values()))
    else:
        out = results
    sys.stdout.write(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
