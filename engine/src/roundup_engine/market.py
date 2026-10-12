"""Market series and its validation (FINANCE-RULES §6, §7, §8)."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from decimal import localcontext

from .money import CONTEXT


class DataError(Exception):
    """A data-quality failure. `code` is one of the FORMAT.md error codes."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Dividend:
    ex_date: date
    pay_date: date | None
    amount: Decimal          # cash per share, raw basis on the ex-date (R-7.4)


@dataclass(frozen=True)
class Split:
    ex_date: date
    ratio: Decimal           # new shares / old shares


@dataclass(frozen=True)
class MarketSeries:
    symbol: str
    calendar: tuple[date, ...]           # calendar-open days, ascending
    closes: dict[date, Decimal]          # raw closes (R-7.1)
    dividends: tuple[Dividend, ...] = ()
    splits: tuple[Split, ...] = ()
    kind: str = "sample"                 # "sample" or "real" (R-12.5)

    @property
    def first_close(self) -> date | None:
        return min(self.closes) if self.closes else None

    @property
    def data_end(self) -> date | None:
        """R-6.5: the last close in the input."""
        return max(self.closes) if self.closes else None

    def last_close_on_or_before(self, day: date) -> date | None:
        best = None
        for d in self.closes:
            if d <= day and (best is None or d > best):
                best = d
        return best

    def checksum(self) -> str:
        """SHA-256 of the canonical market input (R-12.4)."""
        payload = {
            "symbol": self.symbol, "kind": self.kind,
            "calendar": [d.isoformat() for d in self.calendar],
            "closes": {d.isoformat(): str(v) for d, v in sorted(self.closes.items())},
            "dividends": [[x.ex_date.isoformat(), x.pay_date.isoformat() if x.pay_date else None, str(x.amount)]
                          for x in self.dividends],
            "splits": [[x.ex_date.isoformat(), str(x.ratio)] for x in self.splits],
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _jump(a: Decimal, b: Decimal) -> Decimal:
    return max(a / b, b / a)


def validate_series(m: MarketSeries) -> None:
    """Whole-input checks, in FORMAT.md precedence order (window check is done by the caller)."""
    open_days = set(m.calendar)
    end = m.data_end
    # Events after the data end are "no data yet": ignored entirely (R-6.5).
    divs = [x for x in m.dividends if end is not None and x.ex_date <= end]
    splits = [x for x in m.splits if end is not None and x.ex_date <= end]

    for d in m.closes:
        if d not in open_days:
            raise DataError("CLOSE_ON_CLOSED_DAY", d.isoformat())                      # R-6.3(c)
    for ev in [*divs, *splits]:
        if ev.ex_date not in open_days:
            raise DataError("EVENT_NOT_CALENDAR_DAY", ev.ex_date.isoformat())          # R-6.3(c)
    for x in divs:
        if x.pay_date is None:
            raise DataError("MISSING_PAY_DATE", x.ex_date.isoformat())                 # R-8.8
    for x in divs:
        if x.ex_date > x.pay_date:
            raise DataError("EX_AFTER_PAY", x.ex_date.isoformat())                     # R-8.7
    for ev in [*divs, *splits]:
        if ev.ex_date not in m.closes:
            raise DataError("GAP_ON_EVENT", ev.ex_date.isoformat())                    # R-6.3(b)
    with localcontext(CONTEXT):
        for s in splits:                                                               # R-7.5
            if s.ratio <= 0 or s.ratio == 1:
                raise DataError("SPLIT_ADJUSTED_SERIES", f"invalid ratio {s.ratio}")
            before = [d for d in m.closes if d < s.ex_date]
            if not before:
                raise DataError("SPLIT_ADJUSTED_SERIES", f"no close before {s.ex_date}")
            p, q = m.closes[max(before)], m.closes[s.ex_date]
            if not _jump(q * s.ratio, p) < _jump(q, p):
                raise DataError("SPLIT_ADJUSTED_SERIES", s.ex_date.isoformat())
