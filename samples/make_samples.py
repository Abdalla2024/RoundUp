"""Builds the sample bank exports in this folder, reproducibly, from the engine's own purchase generator.

    PYTHONPATH=engine/src .venv/bin/python samples/make_samples.py          # rewrites the files
    PYTHONPATH=engine/src .venv/bin/python samples/make_samples.py --check  # fails if they differ (used by tests)

Ordinary rows come from roundup_engine.generator (seed 2024, window 2024-01-02..2024-03-29, up to 2 a day), so they
are posted card purchases with integer-cent amounts. A fixed set of special rows is added on top. Because we know
exactly what we added, the EXPECTED numbers in expected.json are worked out here by construction (plain integer
arithmetic on cents, R-2.1), not by calling the parser or the engine. The tests compare the app against them.
"""

import csv
import io
import json
import pathlib
import sys

from roundup_engine.generator import generate_transactions

HERE = pathlib.Path(__file__).resolve().parent
START, END, SEED, PER_DAY = "2024-01-02", "2024-03-29", 2024, 2

# (date, description, amount in cents, status, kind). Amounts are positive; refunds are written negative in the
# "signed" layout and in the "Money in" column in the split layout.
SPECIAL = [
    ("2024-01-09", "Bookshop refund", 1250, "posted", "refund"),
    ("2024-01-12", "Transfer to savings", 20000, "posted", "transfer"),
    ("2024-01-18", "Maple Grocery", 3140, "pending", "pending"),
    ("2024-01-19", "Bakery", 457, "cancelled", "cancelled"),
    ("2024-02-06", "Hardware Store", 2000, "posted", "whole_dollar_purchase"),
    ("2024-02-15", "Card payment", 50000, "posted", "payment"),
    ("2024-03-04", "Online shop refund", 899, "posted", "refund"),
]


def rows():
    out = []
    for t in generate_transactions(SEED, START, END, PER_DAY):
        dollars, cents = t["amount"].split(".")
        out.append((t["posted_date"], t["description"].title(), int(dollars) * 100 + int(cents), "posted", "purchase"))
    out += SPECIAL
    return sorted(out, key=lambda r: (r[0], r[4], r[1], r[2]))      # stable and reproducible


def money(cents, negative=False):
    return f"{'-' if negative else ''}{cents // 100}.{cents % 100:02d}"


def write(header, line):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows():
        w.writerow(line(r))
    return buf.getvalue()


def files():
    return {
        # one signed Amount column: purchases positive, refunds negative (the layout of most US bank exports)
        "sample-transactions.csv": write(("Date", "Description", "Amount", "Status"),
            lambda r: (r[0], r[1], money(r[2], r[4] == "refund"), r[3])),
        # separate columns for money out and money in
        "sample-split-columns.csv": write(("Date", "Description", "Money out", "Money in", "Status"),
            lambda r: (r[0], r[1], "" if r[4] == "refund" else money(r[2]), money(r[2]) if r[4] == "refund" else "", r[3])),
        # a column that says debit or credit
        "sample-type-column.csv": write(("Date", "Description", "Amount", "Type", "Status"),
            lambda r: (r[0], r[1], money(r[2]), "credit" if r[4] == "refund" else "debit", r[3])),
    }


def expected():
    rs = rows()
    purchases = [r for r in rs if r[4] in ("purchase", "whole_dollar_purchase")]
    return {
        "window": {"start": START, "end": END},
        "rows": len(rs),
        "parse_summary": {
            "rows": len(rs), "usable": len(rs),
            "non_purchases": sum(r[4] in ("transfer", "payment") for r in rs),
            "credits": sum(r[4] == "refund" for r in rs),
            "not_posted": sum(r[3] in ("pending", "cancelled") for r in rs),
            "whole_dollar": sum(r[2] % 100 == 0 for r in purchases),
        },
        "simulate": {
            "transactions_used": len(purchases),
            "transactions_ignored": len(rs) - len(purchases),
            "contributed": money(sum((100 - r[2] % 100) % 100 for r in purchases)),
        },
    }


if __name__ == "__main__":
    want = {**files(), "expected.json": json.dumps(expected(), indent=1) + "\n"}
    if "--check" in sys.argv:
        bad = [n for n, text in want.items() if (HERE / n).read_text() != text]
        sys.exit(f"out of date: {bad}" if bad else 0)
    for n, text in want.items():
        (HERE / n).write_text(text)
    print("wrote", ", ".join(want))
