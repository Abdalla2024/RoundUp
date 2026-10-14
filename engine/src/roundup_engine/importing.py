"""CSV-row import rules: date column (R-1.2), sign convention (R-1.3), amounts (R-0.1, R-1.5),
duplicates (R-4.1-R-4.5). Input is already-parsed rows (dicts of strings); no file I/O here."""

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime

from .money import InvalidAmount, parse_amount_cents
from .transactions import POSTED_WORDS, normalize_description

CONVENTIONS = ("separate_columns", "type_column", "debits_positive", "debits_negative")


class SignConventionRequired(ValueError):
    """R-1.3: the sign convention cannot be inferred and was not given. No silent default."""


class DuplicateFile(ValueError):
    """R-4.4: the same content was already imported into this session."""


@dataclass(frozen=True)
class ColumnMap:
    date: str | None = None
    posted_date: str | None = None
    amount: str | None = None
    debit: str | None = None
    credit: str | None = None
    type: str | None = None
    status: str | None = None
    description: str | None = None
    external_id: str | None = None
    account: str | None = None


@dataclass(frozen=True)
class NormalizedRow:
    date: date | None
    amount_cents: int
    direction: str
    status: str
    type: str
    description: str
    external_id: str
    account: str
    problem: str | None = None   # "invalid_amount" | "invalid_date" | "zero_amount"

    def dup_key(self):
        """R-4.2 identity: date, amount, direction, normalized description, account."""
        return (self.date, self.amount_cents, self.direction, normalize_description(self.description), self.account)

    def as_fixture(self) -> dict:
        cents = self.amount_cents
        return {"posted_date": self.date.isoformat() if self.date else "",
                "amount": f"{cents // 100}.{cents % 100:02d}" if self.problem != "invalid_amount" else "invalid",
                "direction": self.direction, "status": self.status, "type": self.type,
                "description": self.description}


@dataclass(frozen=True)
class NormalizedFile:
    rows: tuple[NormalizedRow, ...]
    date_column_used: str
    sign_convention: str
    content_hash: str


def _get(row, col):
    return (row.get(col) or "").strip() if col else ""


def _parse_date(text: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _status(text: str, mapped: bool = True) -> str:
    """R-1.4a (owner decision OQ-12, the cautious rule). With no Status column every row is posted. With one, only the
    clearly posted words count; pending and cancelled keep their meaning; anything else, including a blank cell, is
    "unrecognised": left out of the count and flagged until the owner decides."""
    if not mapped:
        return "posted"
    t = normalize_description(text)
    if t == "pending":
        return "pending"
    if t in ("cancelled", "canceled", "void", "voided"):
        return "cancelled"
    return "posted" if t in POSTED_WORDS else "unrecognised"


def infer_sign_convention(cmap: ColumnMap, rows) -> str | None:
    if cmap.debit and cmap.credit:
        return "separate_columns"
    if cmap.type and cmap.amount:
        values = {normalize_description(_get(r, cmap.type)) for r in rows} - {""}
        if values and values <= {"debit", "credit"}:
            return "type_column"
    return None


def normalize_file(rows: list[dict], cmap: ColumnMap, sign_convention: str | None = None) -> NormalizedFile:
    convention = sign_convention or infer_sign_convention(cmap, rows)
    if convention is None:
        raise SignConventionRequired("choose how debits and credits are signed in this file")
    if convention not in CONVENTIONS:
        raise ValueError(f"unknown sign convention {convention!r}")
    date_col = cmap.posted_date or cmap.date                                    # R-1.2
    if not date_col:
        raise ValueError("a date column is required")

    out = []
    for r in rows:
        problem = None
        direction, cents = "debit", 0
        try:
            if convention == "separate_columns":
                d, c = _get(r, cmap.debit), _get(r, cmap.credit)
                if bool(d) == bool(c):
                    raise InvalidAmount("exactly one of debit/credit must be filled")
                direction = "debit" if d else "credit"
                cents = abs(parse_amount_cents(d or c))
            else:
                signed = parse_amount_cents(_get(r, cmap.amount))
                if convention == "type_column":
                    direction = "credit" if normalize_description(_get(r, cmap.type)) == "credit" else "debit"
                elif convention == "debits_positive":
                    direction = "debit" if signed >= 0 else "credit"
                else:
                    direction = "debit" if signed <= 0 else "credit"
                cents = abs(signed)
        except InvalidAmount:
            problem = "invalid_amount"
        day = _parse_date(_get(r, date_col))
        if problem is None and day is None:
            problem = "invalid_date"
        if problem is None and cents == 0:
            problem = "zero_amount"                                              # R-1.5
        out.append(NormalizedRow(day, cents, direction, _status(_get(r, cmap.status), mapped=bool(cmap.status)),
                                 "" if convention == "type_column" else _get(r, cmap.type),
                                 _get(r, cmap.description), _get(r, cmap.external_id), _get(r, cmap.account),
                                 problem))
    mapped = [[_get(r, c) for c in (date_col, cmap.amount, cmap.debit, cmap.credit, cmap.type, cmap.status,
                                     cmap.description, cmap.external_id, cmap.account)] for r in rows]
    digest = hashlib.sha256(json.dumps(mapped).encode()).hexdigest()           # R-4.4
    return NormalizedFile(tuple(out), date_col, convention, digest)


@dataclass
class ImportReport:
    replaced_by_id: int = 0          # R-4.1: same ID, different amount/date, from an earlier file
    possible_duplicates: int = 0     # R-4.2: rows in identical groups within this file (kept)
    excluded_overlap: int = 0        # R-4.3: rows excluded because an earlier file already has them


@dataclass
class ImportSession:
    _hashes: set = field(default_factory=set)
    _by_id: dict = field(default_factory=dict)      # (external_id, account) -> row
    _no_id: list = field(default_factory=list)      # list of (file_index, row)
    _files: int = 0

    def add_file(self, nf: NormalizedFile, keep_overlap: bool = False) -> ImportReport:
        if nf.content_hash in self._hashes:
            raise DuplicateFile("this file was already imported")
        rep = ImportReport()
        with_id = [r for r in nf.rows if r.external_id]
        without = [r for r in nf.rows if not r.external_id]

        for r in with_id:                                                       # R-4.1
            key = (r.external_id, r.account)
            prev = self._by_id.get(key)
            if prev is not None and prev[0] < self._files and (prev[1].amount_cents, prev[1].date) != (r.amount_cents, r.date):
                rep.replaced_by_id += 1
            self._by_id[key] = (self._files, r)       # later file / later row wins

        counts = Counter(r.dup_key() for r in without)                          # R-4.2
        rep.possible_duplicates = sum(n for n in counts.values() if n > 1)

        keep = list(without)
        if not keep_overlap:                                                    # R-4.3
            keep = []
            for account in sorted({r.account for r in without}):
                new = [r for r in without if r.account == account]
                old = [r for _, r in self._no_id if r.account == account]
                new_dates = [r.date for r in new if r.date]
                old_dates = [r.date for r in old if r.date]
                if not new_dates or not old_dates:
                    keep.extend(new)
                    continue
                lo, hi = max(min(new_dates), min(old_dates)), min(max(new_dates), max(old_dates))
                available = Counter(r.dup_key() for r in old if r.date and lo <= r.date <= hi)
                for r in new:
                    k = r.dup_key()
                    if r.date and lo <= r.date <= hi and available[k] > 0:
                        available[k] -= 1
                        rep.excluded_overlap += 1
                    else:
                        keep.append(r)
        self._no_id.extend((self._files, r) for r in keep)
        self._hashes.add(nf.content_hash)
        self._files += 1
        return rep

    @property
    def transactions(self) -> list[NormalizedRow]:
        rows = [r for _, r in self._no_id] + [r for _, r in self._by_id.values()]
        return rows
