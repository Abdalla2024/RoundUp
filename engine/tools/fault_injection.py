"""Fault injection: break one rule at a time in a scratch copy of the engine and check a test fails.

    python tools/fault_injection.py

Each mutation is a list of exact (old, new) source replacements; `old` must occur exactly once.
A mutation that leaves every test passing has "survived", which means the tests have a gap.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent.parent
PY = HERE / ".venv" / "bin" / "python"
if not PY.exists():                      # CI and the root README setup: use the running interpreter
    PY = pathlib.Path(sys.executable)

SPLIT_BLOCK = (
    "            if d in splits:                                                            # R-8.1 (1)\n"
    "                shares *= splits[d].ratio\n"
)
DIV_LOOP = "            for x in divs:                                                             # R-8.1 (2), R-8.2/8.3\n"
BUY_BLOCK = (
    "            for b, delayed in plan.get(d, []):                                         # R-8.1 (3) round-ups\n"
    "                cash = cents_to_decimal(b.cents)\n"
    "                got = cash / price\n"
    "                shares += got\n"
    "                bought_cents += b.cents\n"
    "                buys.append(Buy(d, \"roundup\", cash, price, got, delayed, b.cutoff, b.purchase_dates))\n"
)

S = "src/roundup_engine/"
MUTATIONS = [
    ("unrecognised status counted as a purchase", "R-1.4a", S + "transactions.py",
     [("elif status not in POSTED_WORDS:", "elif False:")]),
    ("only 'posted' counts (settled/cleared/completed dropped)", "R-1.4a", S + "transactions.py",
     [('POSTED_WORDS = ("posted", "settled", "cleared", "completed")', 'POSTED_WORDS = ("posted",)')]),
    ("window with no trading day accepted", "R-12.1", S + "simulate.py",
     [("if not any(cfg.start <= d <= cfg.end for d in m.closes):", "if False:")]),
    # id, rule, file, [(old, new), ...]
    ("whole-dollar rounds to $1", "R-2.2", S + "roundup.py",
     [("return (100 - amount_cents % 100) % 100", "return 100 - amount_cents % 100")]),
    ("card payments round up (H5)", "R-1.4", S + "transactions.py",
     [('NON_PURCHASE_WORDS = frozenset({"payment", ', 'NON_PURCHASE_WORDS = frozenset({')]),
    ("keyword substring match (fee in coffee)", "R-1.4", S + "transactions.py",
     [("if NON_PURCHASE_WORDS.intersection(w):",
       "if any(k in normalize_description(description) for k in NON_PURCHASE_WORDS):")]),
    ("non-purchase type ignored", "R-1.4", S + "transactions.py",
     [("if normalize_description(type_) in NON_PURCHASE_TYPES:", "if False:")]),
    ("refunds/credits round up", "R-1.8", S + "transactions.py",
     [('if row.get("direction") != "debit":', 'if False:')]),
    # With R-1.4a (stage 6) pending and cancelled rows are ignored because they are not in the posted list, so the old
    # mutations (delete the explicit branches) are equivalent and can never fail. These break the list itself instead.
    ("pending rows round up", "R-1.4", S + "transactions.py",
     [('elif status == "pending":', 'elif False:'),
      ('POSTED_WORDS = ("posted", "settled", "cleared", "completed")', 'POSTED_WORDS = ("posted", "settled", "cleared", "completed", "pending")')]),
    ("cancelled rows round up", "R-3.2", S + "transactions.py",
     [('elif status in ("cancelled", "canceled", "void", "voided"):', 'elif False:'),
      ('POSTED_WORDS = ("posted", "settled", "cleared", "completed")',
       'POSTED_WORDS = ("posted", "settled", "cleared", "completed", "cancelled", "canceled", "void", "voided")')]),
    ("out-of-window rows used", "R-1.6", S + "transactions.py",
     [("elif not (start <= day <= end):", "elif False:")]),
    ("3-decimal amounts accepted", "R-0.1", S + "money.py",
     [(r'(\.[0-9]{1,2})?$")', r'(\.[0-9]{1,3})?$")')]),
    ("non-ASCII digits accepted (independent-tester finding)", "R-0.1", S + "money.py",
     [(r'_AMOUNT = re.compile(r"^([0-9]+|[0-9]{1,3}(,[0-9]{3})+)(\.[0-9]{1,2})?$")',
       r'_AMOUNT = re.compile(r"^(\d+|\d{1,3}(,\d{3})+)(\.\d{1,2})?$")')]),
    ("display rounds half-up", "R-0.4", S + "money.py",
     [("q = snapped.quantize(exp, rounding=ROUND_HALF_EVEN, context=CONTEXT)",
       "q = snapped.quantize(exp, rounding='ROUND_HALF_UP', context=CONTEXT)")]),
    ("tie snap removed (cross-check finding)", "R-0.4", S + "money.py",
     [("q = snapped.quantize(exp, rounding=ROUND_HALF_EVEN, context=CONTEXT)",
       "q = value.quantize(exp, rounding=ROUND_HALF_EVEN, context=CONTEXT)")]),
    ("float trap removed", "R-0.5", S + "money.py",
     [("traps=[InvalidOperation, DivisionByZero, Overflow, FloatOperation])",
       "traps=[InvalidOperation, DivisionByZero, Overflow])")]),
    ("threshold uses > instead of >=", "R-5.2", S + "strategies.py",
     [("if acc >= THRESHOLD_CENTS:", "if acc > THRESHOLD_CENTS:")]),
    ("threshold carries the excess", "R-5.2", S + "strategies.py",
     [("batches.append(Batch(day, acc, tuple(members)))\n                acc, members = 0, []",
       "batches.append(Batch(day, THRESHOLD_CENTS, tuple(members)))\n                acc, members = acc - THRESHOLD_CENTS, []")]),
    ("weekly cut-off on Saturday", "R-5.2", S + "strategies.py",
     [("return day + timedelta(days=6 - day.weekday())", "return day + timedelta(days=(5 - day.weekday()) % 7)")]),
    ("same-day execution (look-ahead)", "R-5.1/R-11.1", S + "simulate.py",
     [("ex = _first_after(sessions, b.cutoff, inclusive=False)", "ex = _first_after(sessions, b.cutoff, inclusive=True)")]),
    # Note: deleting the `ex <= cfg.end` guard alone is an equivalent mutant (the day loop never visits
    # days after `end`), so R-5.4 is broken by extending the loop instead.
    ("buys and valuation run past the end date", "R-5.4", S + "simulate.py",
     [("if ex is not None and ex <= cfg.end:", "if ex is not None:"),
      ("for d in m.calendar if cfg.start <= d <= cfg.end]", "for d in m.calendar if cfg.start <= d <= m.data_end]")]),
    ("data-gap flag never set", "R-6.2", S + "simulate.py",
     [("plan.setdefault(ex, []).append((b, first_open != ex))", "plan.setdefault(ex, []).append((b, False))")]),
    ("carried flag never set", "R-6.4", S + "simulate.py",
     [("            carried = True ", "            carried = False ")]),
    ("gap run limit 4 instead of 3", "R-6.3(a)", S + "simulate.py",
     [("MAX_GAP_RUN = 3", "MAX_GAP_RUN = 4")]),
    ("window check removed", "R-12.1", S + "simulate.py",
     [('        raise DataError("WINDOW_OUTSIDE_DATA")', "        pass")]),
    ("gap-on-event check removed (H1)", "R-6.3(b)", S + "market.py",
     [('raise DataError("GAP_ON_EVENT", ev.ex_date.isoformat())', "pass")]),
    ("split-basis check removed (H4)", "R-7.5", S + "market.py",
     [("if not _jump(q * s.ratio, p) < _jump(q, p):", "if False:")]),
    ("missing pay date accepted", "R-8.8", S + "market.py",
     [('raise DataError("MISSING_PAY_DATE", x.ex_date.isoformat())', "pass")]),
    ("ex after pay accepted", "R-8.7", S + "market.py",
     [("if x.ex_date > x.pay_date:", "if False:")]),
    ("dividend applied before same-day split (H3)", "R-8.1/R-8.2", S + "simulate.py",
     [(SPLIT_BLOCK, ""), (BUY_BLOCK, SPLIT_BLOCK + BUY_BLOCK)]),
    ("entitlement includes shares bought on the ex-date", "R-8.2", S + "simulate.py",
     [(BUY_BLOCK, ""), (DIV_LOOP, BUY_BLOCK + DIV_LOOP)]),
    ("dividend follows later splits (H2)", "R-8.3", S + "simulate.py",
     [("                shares *= splits[d].ratio\n",
       "                shares *= splits[d].ratio\n"
       "                for e in earned:\n"
       "                    if not e.reinvested and e.pay_date > d:\n"
       "                        e.amount *= splits[d].ratio\n")]),
    ("receivable not counted in value", "R-8.4", S + "simulate.py",
     [("recv = sum((e.amount for e in earned if e.pay_date > asof), Decimal(0))", "recv = Decimal(0)")]),
    ("reinvest at ex-date", "R-8.5", S + "simulate.py",
     [("reinvest_on = _first_after(sessions, x.pay_date, inclusive=True)", "reinvest_on = d")]),
    ("reinvest toggle ignored", "R-8.6", S + "simulate.py", [("if cfg.reinvest:", "if True:")]),
    ("dividends paid counts unpaid", "R-13.1", S + "simulate.py",
     [("dividends_paid=sum((e.amount for e in earned if e.pay_date <= cfg.end), Decimal(0)),",
       "dividends_paid=sum((e.amount for e in earned), Decimal(0)),")]),
    ("gain % shows 0.00 instead of n/a", "R-13.1", S + "scenario.py",
     [('"gain_pct": "n/a" if pct is None else display_pct(pct),', '"gain_pct": "0.00" if pct is None else display_pct(pct),')]),
    ("chart thinning boundary 365 instead of 366 days", "display", S + "scenario.py",
     [("DAILY_MAX_DAYS = 366", "DAILY_MAX_DAYS = 365")]),
    ("weekly chart keeps the week's first day", "display", S + "scenario.py",
     [("if i == len(points) - 1 or (date.fromisoformat(points[i + 1][\"date\"]).isocalendar()[:2]",
       "if i == len(points) - 1 or (i == 0) or (date.fromisoformat(points[i - 1][\"date\"]).isocalendar()[:2]")]),
    ("deepest dip: latest day wins ties", "R-13.1", S + "simulate.py",
     [("if below > 0 and (dip is None or below > dip.below_by):",
       "if below > 0 and (dip is None or below >= dip.below_by):")]),
    ("deepest dip: 1e-27 residue counts as a dip", "R-13.1", S + "simulate.py",
     [("below = (added - pt.value).quantize(SNAP)", "below = added - pt.value")]),
    ("cash split swapped", "R-13.1", S + "simulate.py",
     [("roundups_waiting=cents_to_decimal(rcash), dividends_as_cash=dcash,",
       "roundups_waiting=dcash, dividends_as_cash=cents_to_decimal(rcash),")]),
    ("posted date not preferred", "R-1.2", S + "importing.py",
     [("date_col = cmap.posted_date or cmap.date", "date_col = cmap.date or cmap.posted_date")]),
    ("silent sign-convention default", "R-1.3", S + "importing.py",
     [('        raise SignConventionRequired("choose how debits and credits are signed in this file")',
       '        convention = "debits_positive"')]),
    ("overlapping files double-count", "R-4.3", S + "importing.py", [("if not keep_overlap:", "if False:")]),
    ("same file imported twice", "R-4.4", S + "importing.py",
     [('            raise DuplicateFile("this file was already imported")', "            pass")]),
]


IGNORE = shutil.ignore_patterns(".venv", "__pycache__", ".hypothesis", "*.egg-info", ".git", "node_modules")


def run_one(mut) -> tuple[bool, str]:
    name, rule, rel, edits = mut
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "engine"
        shutil.copytree(HERE, work, ignore=IGNORE)
        shutil.copytree(HERE.parent / "crosscheck", pathlib.Path(tmp) / "crosscheck", ignore=IGNORE)
        for doc in HERE.parent.glob("*.md"):            # tests read repo-level docs (e.g. SCENARIO-MODEL.md)
            shutil.copy(doc, pathlib.Path(tmp) / doc.name)
        path = work / rel
        src = path.read_text()
        for old, new in edits:
            if src.count(old) != 1:
                return False, f"MUTATION NOT APPLIED ({src.count(old)} matches): {old[:60]!r}"
            src = src.replace(old, new)
        path.write_text(src)
        proc = subprocess.run([str(PY), "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "--no-header"],
                              cwd=work, capture_output=True, text=True)
        failed = [ln for ln in proc.stdout.splitlines() if ln.startswith("FAILED")]
        if proc.returncode != 0 and not failed:
            # A collection/import error is a harness problem, never a "catch".
            return False, "HARNESS ERROR: " + proc.stdout.strip().splitlines()[-1]
        return bool(failed), failed[0][7:90] if failed else proc.stdout.strip().splitlines()[-1]


def main() -> int:
    # Baseline: the unmutated copy must pass, otherwise every "catch" below would be meaningless.
    ok, info = run_one(("baseline", "-", "src/roundup_engine/__init__.py", []))
    if ok:
        print(f"HARNESS BROKEN: the unmutated copy fails: {info}")
        return 2
    print(f"baseline (no mutation): passes ({info})")
    survived = 0
    print(f"{'rule':<12} {'mutation':<48} result")
    for mut in MUTATIONS:
        caught, info = run_one(mut)
        survived += not caught
        print(f"{mut[1]:<12} {mut[0]:<48} {'caught by ' + info if caught else 'SURVIVED: ' + info}")
    print(f"\n{len(MUTATIONS)} mutations, {len(MUTATIONS) - survived} caught, {survived} survived")
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
