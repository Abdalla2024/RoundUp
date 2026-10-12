"""Which rows become round-ups (FINANCE-RULES §1, §3)."""

import re
from dataclasses import dataclass
from datetime import date

from .money import InvalidAmount, parse_amount_cents

# R-1.4: non-purchase debit detection. Words match whole runs of letters and digits.
NON_PURCHASE_TYPES = frozenset({"payment", "transfer", "atm", "fee", "interest", "loan"})
NON_PURCHASE_WORDS = frozenset({"payment", "transfer", "xfer", "atm", "withdrawal", "zelle", "venmo",
                                "autopay", "loan", "fee", "interest"})
NON_PURCHASE_PHRASES = (("cash", "app"),)

_WORD = re.compile(r"[^\W_]+")


@dataclass(frozen=True)
class Transaction:
    date: date
    amount_cents: int
    description: str


def normalize_description(text: str) -> str:
    """R-4.5: trimmed, case-folded, internal whitespace collapsed."""
    return " ".join((text or "").split()).casefold()


def words(text: str) -> list[str]:
    return _WORD.findall(normalize_description(text))


def is_non_purchase(type_: str, description: str) -> bool:
    if normalize_description(type_) in NON_PURCHASE_TYPES:
        return True
    w = words(description)
    if NON_PURCHASE_WORDS.intersection(w):
        return True
    for phrase in NON_PURCHASE_PHRASES:
        n = len(phrase)
        if any(tuple(w[i:i + n]) == phrase for i in range(len(w) - n + 1)):
            return True
    return False


def select_purchases(rows, start: date, end: date):
    """Apply R-0.1, R-1.4, R-1.5, R-1.6, R-1.8, R-3.2 to fixture-shaped rows.

    Returns (used, ignored) where `used` are posted purchase debits in the window (including
    whole-dollar ones) and `ignored` is a list of (row_index, reason).
    """
    used, ignored = [], []
    for i, row in enumerate(rows):
        try:
            cents = parse_amount_cents(row.get("amount"))
        except InvalidAmount:
            ignored.append((i, "invalid_amount"))
            continue
        if cents < 0:
            ignored.append((i, "invalid_amount"))
            continue
        try:
            day = date.fromisoformat(row.get("posted_date") or "")
        except ValueError:
            ignored.append((i, "invalid_date"))
            continue
        status = normalize_description(row.get("status") or "posted")
        if row.get("direction") != "debit":
            reason = "credit"                      # includes refunds (R-1.8, R-3.1)
        elif status == "pending":
            reason = "pending"
        elif status in ("cancelled", "canceled", "void", "voided"):
            reason = "cancelled"                   # R-3.2
        elif cents == 0:
            reason = "zero_amount"                 # R-1.5
        elif row.get("category") == "non_purchase" or (
                row.get("category") != "purchase"
                and is_non_purchase(row.get("type") or "", row.get("description") or "")):
            reason = "non_purchase"                # R-1.4 (an explicit category overrides keywords)
        elif not (start <= day <= end):
            reason = "outside_window"              # R-1.6
        else:
            used.append(Transaction(day, cents, row.get("description") or ""))
            continue
        ignored.append((i, reason))
    return used, ignored
