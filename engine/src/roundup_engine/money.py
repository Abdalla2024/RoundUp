"""Number handling (FINANCE-RULES §0): integer cents in, Decimal inside, rounding only at display."""

import re
from decimal import (ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, FloatOperation, InvalidOperation,
                     Overflow)

# R-0.3 / R-0.5: precision 28, half-even, and mixing in a float raises.
CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN,
                  traps=[InvalidOperation, DivisionByZero, Overflow, FloatOperation])

CENT = Decimal("0.01")
SHARE_DISPLAY = Decimal("0.000001")

_AMOUNT = re.compile(r"^(\d+|\d{1,3}(,\d{3})+)(\.\d{1,2})?$")
_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")


class InvalidAmount(ValueError):
    pass


def parse_amount_cents(text) -> int:
    """R-0.1: parse a money string to integer cents. More than 2 decimals is rejected, never rounded.

    Accepts an optional leading '-', '$', thousands separators, or accounting parentheses.
    """
    if not isinstance(text, str):
        raise InvalidAmount(f"amount must be a string, got {type(text).__name__}")
    t = text.strip()
    negative = False
    if t.startswith("(") and t.endswith(")"):
        negative, t = True, t[1:-1].strip()
    if t.startswith("-"):
        if negative:
            raise InvalidAmount(text)
        negative, t = True, t[1:]
    if t.startswith("$"):
        t = t[1:]
    if not _AMOUNT.match(t):
        raise InvalidAmount(text)
    whole, _, frac = t.partition(".")
    cents = int(whole.replace(",", "")) * 100 + int(frac.ljust(2, "0") if frac else "0")
    return -cents if negative else cents


def parse_decimal(text) -> Decimal:
    """Parse a market number (price, dividend, ratio) from a plain decimal string."""
    if not isinstance(text, str) or not _DECIMAL.match(text.strip()):
        raise ValueError(f"not a plain decimal string: {text!r}")
    return Decimal(text.strip())


def cents_to_decimal(cents: int) -> Decimal:
    return Decimal(cents).scaleb(-2)


def _q(value: Decimal, exp: Decimal) -> str:
    q = value.quantize(exp, rounding=ROUND_HALF_EVEN, context=CONTEXT)
    if q.is_zero():
        q = abs(q)  # never display "-0.00"
    return format(q, "f")


def display_money(value: Decimal) -> str:
    """R-0.4: nearest cent, half-even."""
    return _q(value, CENT)


def display_shares(value: Decimal) -> str:
    """R-0.4 / R-9.2: 6 decimal places, half-even."""
    return _q(value, SHARE_DISPLAY)


def display_pct(value: Decimal) -> str:
    """R-13.1: 2 decimal places, half-even."""
    return _q(value, CENT)
