"""R-0.x number handling and R-2.x round-up definition."""

from decimal import Decimal, FloatOperation

import pytest

from roundup_engine.money import (CONTEXT, InvalidAmount, display_money, display_pct, display_shares,
                                  parse_amount_cents)
from roundup_engine.roundup import roundup_cents


@pytest.mark.parametrize("s,cents", [("4.37", 437), ("4", 400), ("4.5", 450), ("0.01", 1), ("1000.00", 100000),
                                     ("$1,234.56", 123456), ("  7.10 ", 710), ("-3.00", -300), ("(4.37)", -437)])
def test_parse_amount(s, cents):
    assert parse_amount_cents(s) == cents


@pytest.mark.parametrize("s", ["4.375", "abc", "", "1.2.3", "1e3", "NaN", "4.37.", "--4", "4,37"])
def test_parse_amount_rejects(s):
    with pytest.raises(InvalidAmount):
        parse_amount_cents(s)


def test_parse_amount_rejects_float():
    with pytest.raises(InvalidAmount):
        parse_amount_cents(4.37)


@pytest.mark.parametrize("cents,r", [(437, 63), (400, 0), (1, 99), (99, 1), (100000, 0), (101, 99)])
def test_roundup(cents, r):
    assert roundup_cents(cents) == r


def test_roundup_requires_positive_int():
    with pytest.raises(ValueError):
        roundup_cents(0)
    with pytest.raises(TypeError):
        roundup_cents(Decimal("4.37"))


def test_display_half_even():
    assert display_money(Decimal("1.005")) == "1.00"
    assert display_money(Decimal("1.015")) == "1.02"
    assert display_money(Decimal("-0.005")) == "0.00"
    assert display_money(Decimal("4.99999999999999999999999999")) == "5.00"
    assert display_shares(Decimal("0.0000005")) == "0.000000"
    assert display_shares(Decimal("0.0000015")) == "0.000002"
    assert display_pct(Decimal("12.345")) == "12.34"


def test_context_traps_float_operation():
    assert CONTEXT.prec == 28
    assert CONTEXT.traps[FloatOperation]
    with pytest.raises(FloatOperation):
        CONTEXT.create_decimal(1.1)


def test_r_0_4_exact_ties_survive_28_digit_residue():
    """Regression (cross-check finding, scenario R-5288): an exact half-cent tie computed as
    9.485000000000000000000000001 must still round half-even to 9.48."""
    assert display_money(Decimal("9.485000000000000000000000001")) == "9.48"
    assert display_money(Decimal("9.484999999999999999999999999")) == "9.48"
    assert display_money(Decimal("9.495000000000000000000000001")) == "9.50"
    assert display_shares(Decimal("0.0000025000000000000000000001")) == "0.000002"
