"""CSV parsing for /v1/transactions/parse. Classification and normalisation are done by the engine.

Safety: size and row caps, NUL/binary rejection, bounded field size, echoed text neutralised against
spreadsheet formula injection (OWASP CSV Injection), descriptions never returned.
"""

import csv
import io
import re

from roundup_engine.importing import ColumnMap, ImportSession, SignConventionRequired, normalize_file
from roundup_engine.transactions import is_non_purchase

from .errors import ApiError
from .schemas import AMOUNT

MAX_ROWS = 20_000
MAX_COLUMNS = 50
MAX_FIELD = 10_000
FORMULA_START = ("=", "+", "-", "@", "\t", "\r", "\n", "＝", "＋", "－", "＠")

csv.field_size_limit(MAX_FIELD)


COLUMN_WORDS = {"amount": "the amount", "type": "debit or credit", "debit": "money out", "credit": "money in"}


def neutralise(text: str) -> str:
    """Prefix a single quote so a spreadsheet treats the value as text (OWASP CSV Injection)."""
    return "'" + text if text.startswith(FORMULA_START) else text


def _bad(msg: str) -> ApiError:
    return ApiError(422, "CSV_INVALID", msg)


def parse_csv(text: str, mapping: dict, sign_convention: str | None) -> dict:
    text = text.removeprefix("\ufeff")              # Excel's UTF-8 byte-order mark
    if "\x00" in text:
        raise _bad("The file looks like binary data, not a CSV file.")
    if not text.strip():
        raise _bad("The file is empty.")
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error:
        raise _bad("The file could not be read as CSV. Check for unmatched quotes, or a cell that is very long "
                   f"(the limit is {MAX_FIELD:,} characters).") from None
    header = rows[0]
    numbered = [(i + 2, r) for i, r in enumerate(rows[1:]) if any(c.strip() for c in r)]   # header is row 1
    data = [r for _, r in numbered]
    if len(header) > MAX_COLUMNS or any(len(h) > 100 for h in header):
        raise _bad("The file has too many columns or a column name is too long.")
    if len(data) > MAX_ROWS:
        raise _bad(f"The file has more than {MAX_ROWS:,} rows.")
    columns = [h.strip() for h in header]
    used = {k: v for k, v in mapping.items() if v is not None}
    missing = [k for k, v in used.items() if v not in columns]
    if missing:                                    # user-supplied names are never echoed in errors
        raise ApiError(422, "CSV_INVALID", "Some chosen columns are not in the file. Check the column choices.",
                       fields=[f"mapping.{k}" for k in missing])
    needs = {"separate_columns": ("debit", "credit"), "type_column": ("amount", "type"),
             "debits_positive": ("amount",), "debits_negative": ("amount",)}
    if sign_convention in needs:                   # name the missing column (stage-5 reviewer L9)
        missing_cols = [k for k in needs[sign_convention] if not used.get(k)]
        if missing_cols:
            raise ApiError(422, "INVALID_INPUT", "Choose which column holds " + " and which holds ".join(
                COLUMN_WORDS[k] for k in missing_cols) + ".",
                fields=["sign_convention"] + [f"mapping.{k}" for k in missing_cols])
    if not (used.get("date") or used.get("posted_date")):
        raise _bad("Choose which column holds the date.")
    dict_rows = [{c: (r[i] if i < len(r) else "") for i, c in enumerate(columns)} for r in data]
    try:
        nf = normalize_file(dict_rows, ColumnMap(**used), sign_convention=sign_convention)
    except SignConventionRequired:
        raise ApiError(422, "SIGN_CONVENTION_REQUIRED", "We can't tell which amounts are purchases and which "
                       "are refunds or payments. Choose how this file signs its amounts.") from None
    report = ImportSession().add_file(nf)
    out, problems, non_purchases = [], {"invalid_amount": 0, "invalid_date": 0, "zero_amount": 0}, 0
    credits = not_posted = whole_dollar = 0          # counts of rows (stage 6), so the check step can say why rows add nothing
    for i, r in enumerate(nf.rows):
        category = "non_purchase" if is_non_purchase(r.type, r.description) else "purchase"
        non_purchases += category == "non_purchase"
        f = r.as_fixture()
        problem = r.problem
        if problem is None and not re.fullmatch(AMOUNT, f["amount"]):   # same limit as /v1/simulate (reviewer M3)
            problem = "invalid_amount"
        if problem:
            problems[problem] += 1
        credits += r.direction == "credit"
        not_posted += r.status in ("pending", "cancelled")
        whole_dollar += (problem is None and r.direction == "debit" and r.status == "posted" and category == "purchase"
                         and re.fullmatch(r"\d+(\.00)?", f["amount"]) is not None)
        out.append({"row": numbered[i][0], "posted_date": f["posted_date"] or None,
                    "amount": f["amount"] if problem != "invalid_amount" else None,
                    "direction": r.direction, "status": r.status, "category": category, "problem": problem})
    return {"columns": [neutralise(c) for c in columns], "date_column_used": neutralise(nf.date_column_used),
            "sign_convention": nf.sign_convention, "transactions": out,
            "summary": {"rows": len(out), "usable": sum(1 for x in out if x["problem"] is None),
                        "problems": problems, "non_purchases": non_purchases, "credits": credits,
                        "not_posted": not_posted, "whole_dollar": whole_dollar,
                        "possible_duplicates": report.possible_duplicates}}
