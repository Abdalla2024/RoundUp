"""R-13.4: composition of the end value in basis points (largest remainder, ties to the earlier part)."""

from decimal import Decimal

from hypothesis import given, settings, strategies as st

from roundup_engine.composition import KEYS, share_bp


def D(x):
    return Decimal(x)


def test_exact_shares():
    assert share_bp([D("4.80"), D("0"), D("0.20"), D("0")], D("5.00")) == [9600, 0, 400, 0]
    assert share_bp([D("6.00"), D("0.40"), D("0"), D("0")], D("6.40")) == [9375, 625, 0, 0]


def test_the_leftover_basis_point_goes_to_the_larger_remainder():
    assert share_bp([D("1.53"), D("0.80"), D("0"), D("0")], D("2.33")) == [6567, 3433, 0, 0]


def test_a_tie_goes_to_the_earlier_part():
    # three equal thirds: floors 3333, 3333, 3333 leave 1; all remainders equal (.33...), so the earliest part gets it
    assert share_bp([D("1"), D("1"), D("1"), D("0")], D("3")) == [3334, 3333, 3333, 0]
    # three tied thirds and a zero part: one point is left over and the earliest tied part takes it
    assert share_bp([D("1"), D("1"), D("0"), D("1")], D("3")) == [3334, 3333, 0, 3333]


def test_zero_ending_value_gives_all_zero():
    assert share_bp([D("0"), D("0"), D("0"), D("0")], D("0")) == [0, 0, 0, 0]


def test_the_keys_are_in_the_documented_order():
    assert KEYS == ("shares", "roundups_waiting", "dividends_as_cash", "receivables")


amount = st.decimals(min_value=D("0"), max_value=D("100000"), places=4, allow_nan=False, allow_infinity=False)


@settings(max_examples=300, deadline=None)
@given(parts=st.lists(amount, min_size=4, max_size=4))
def test_p_shares_add_to_10000_and_each_is_within_one_point_of_exact(parts):
    total = sum(parts)
    out = share_bp(parts, total)
    if total == 0:
        assert out == [0, 0, 0, 0]
        return
    assert sum(out) == 10000 and all(0 <= b <= 10000 for b in out)
    for p, b in zip(parts, out):
        exact = p * 10000 / total
        assert abs(Decimal(b) - exact) < 1                       # never more than one basis point from the exact share
        assert b >= int(exact)                                    # never below the floor
