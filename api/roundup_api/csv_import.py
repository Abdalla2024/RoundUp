"""CSV parsing for /v1/transactions/parse. Classification and normalisation are done by the engine.

Safety: size and row caps, NUL/binary rejection, bounded field size, echoed text neutralised against
spreadsheet formula injection (OWASP CSV Injection), descriptions never returned.
"""

import csv
import io

from roundup_engine.importing import ColumnMap, ImportSession, SignConventionRequired, normalize_file
from roundup_engine.transactions import is_non_purchase

from .errors import ApiError

MAX_ROWS = 20_000
MAX_COLUMNS = 50
MAX_FIELD = 10_000
FORMULA_START = ("=", "+", "-", "@", "\t", "\r", "\n", "＝", "＋", "－", "＠")

csv.field_size_limit(MAX_FIELD)


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
        raise _bad("The file could not be read as CSV. Check for unmatched quotes.") from None
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
    needs = {"separate_columns": ("debit", "credit"), "type_column": ("type", "amount"),
             "debits_positive": ("amount",), "debits_negative": ("amount",)}
    if sign_convention and not all(used.get(k) for k in needs[sign_convention]):
        raise ApiError(422, "INVALID_INPUT", "The chosen sign convention does not match the chosen columns.",
                       fields=["sign_convention"])
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
    for i, r in enumerate(nf.rows):
        category = "non_purchase" if is_non_purchase(r.type, r.description) else "purchase"
        non_purchases += category == "non_purchase"
        if r.problem:
            problems[r.problem] += 1
        f = r.as_fixture()
        out.append({"row": numbered[i][0], "posted_date": f["posted_date"] or None,
                    "amount": f["amount"] if r.problem != "invalid_amount" else None,
                    "direction": r.direction, "status": r.status, "category": category, "problem": r.problem})
    return {"columns": [neutralise(c) for c in columns], "date_column_used": neutralise(nf.date_column_used),
            "sign_convention": nf.sign_convention, "transactions": out,
            "summary": {"rows": len(out), "usable": sum(1 for x in out if x["problem"] is None),
                        "problems": problems, "non_purchases": non_purchases,
                        "possible_duplicates": report.possible_duplicates}}
