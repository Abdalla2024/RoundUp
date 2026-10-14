"""Import rules: R-1.2 date column, R-1.3 sign convention, R-0.1 amounts, R-4.x duplicates."""

import pytest

from roundup_engine.importing import (ColumnMap, DuplicateFile, ImportSession, SignConventionRequired,
                                      normalize_file)

CARD = ColumnMap(date="Trans Date", posted_date="Post Date", amount="Amount", description="Description")


def rows(*items):
    return [dict(zip(("Trans Date", "Post Date", "Amount", "Description"), it)) for it in items]


def test_r_1_2_posted_date_preferred_and_recorded():
    nf = normalize_file(rows(("2024-01-02", "2024-01-04", "4.37", "COFFEE")), CARD, sign_convention="debits_positive")
    assert nf.date_column_used == "Post Date"
    assert nf.rows[0].date.isoformat() == "2024-01-04"


def test_r_1_2_single_date_column():
    cmap = ColumnMap(date="Date", amount="Amount", description="Description")
    nf = normalize_file([{"Date": "2024-01-02", "Amount": "4.37", "Description": "X"}], cmap,
                        sign_convention="debits_positive")
    assert nf.date_column_used == "Date"


def test_r_1_3_no_silent_default():
    with pytest.raises(SignConventionRequired):
        normalize_file(rows(("2024-01-02", "2024-01-02", "4.37", "COFFEE")), CARD)


def test_r_1_3_inferred_from_separate_columns():
    cmap = ColumnMap(date="Date", debit="Debit", credit="Credit", description="Desc")
    nf = normalize_file([{"Date": "2024-01-02", "Debit": "4.37", "Credit": "", "Desc": "COFFEE"},
                         {"Date": "2024-01-03", "Debit": "", "Credit": "20.00", "Desc": "REFUND"}], cmap)
    assert nf.sign_convention == "separate_columns"
    assert [(r.direction, r.amount_cents) for r in nf.rows] == [("debit", 437), ("credit", 2000)]


def test_r_1_3_inferred_from_type_column():
    cmap = ColumnMap(date="Date", amount="Amount", type="Type", description="Desc")
    nf = normalize_file([{"Date": "2024-01-02", "Amount": "4.37", "Type": "DEBIT", "Desc": "COFFEE"},
                         {"Date": "2024-01-03", "Amount": "20.00", "Type": "Credit", "Desc": "REFUND"}], cmap)
    assert nf.sign_convention == "type_column"
    assert [r.direction for r in nf.rows] == ["debit", "credit"]


def test_r_1_3_explicit_conventions():
    pos = normalize_file(rows(("2024-01-02", "2024-01-02", "4.37", "A"), ("2024-01-02", "2024-01-02", "-20.00", "B")),
                         CARD, sign_convention="debits_positive")
    neg = normalize_file(rows(("2024-01-02", "2024-01-02", "-4.37", "A"), ("2024-01-02", "2024-01-02", "20.00", "B")),
                         CARD, sign_convention="debits_negative")
    for nf in (pos, neg):
        assert [(r.direction, r.amount_cents) for r in nf.rows] == [("debit", 437), ("credit", 2000)]


def test_r_0_1_invalid_amount_row_rejected_not_rounded():
    nf = normalize_file(rows(("2024-01-02", "2024-01-02", "4.375", "A")), CARD, sign_convention="debits_positive")
    assert nf.rows[0].problem == "invalid_amount"


def test_r_1_5_zero_amount_flagged():
    nf = normalize_file(rows(("2024-01-02", "2024-01-02", "0.00", "A")), CARD, sign_convention="debits_positive")
    assert nf.rows[0].problem == "zero_amount"


def _file(*items, account="card"):
    cmap = ColumnMap(date="Date", amount="Amount", description="Desc", external_id="Id", account="Acct")
    data = [{"Date": d, "Amount": a, "Desc": desc, "Id": i, "Acct": account} for d, a, desc, i in items]
    return normalize_file(data, cmap, sign_convention="debits_positive")


def test_r_4_1_same_id_latest_file_wins_and_is_flagged():
    s = ImportSession()
    s.add_file(_file(("2024-01-02", "20.00", "DINER", "T1")))
    rep = s.add_file(_file(("2024-01-02", "24.00", "DINER", "T1"), ("2024-01-05", "3.00", "BUS", "T2")))
    kept = {(r.external_id, r.amount_cents) for r in s.transactions}
    assert kept == {("T1", 2400), ("T2", 300)}
    assert rep.replaced_by_id == 1


def test_r_4_1_same_id_within_file_later_row_wins():
    s = ImportSession()
    s.add_file(_file(("2024-01-02", "20.00", "DINER", "T1"), ("2024-01-02", "24.00", "DINER", "T1")))
    assert [r.amount_cents for r in s.transactions] == [2400]


def test_r_4_2_identical_rows_without_id_kept_and_flagged():
    s = ImportSession()
    rep = s.add_file(_file(("2024-01-02", "3.50", "Coffee  Shop", ""), ("2024-01-02", "3.50", "COFFEE SHOP", "")))
    assert len(s.transactions) == 2
    assert rep.possible_duplicates == 2


def test_r_4_3_overlap_excluded_by_default_multiset():
    s = ImportSession()
    s.add_file(_file(("2024-01-10", "3.50", "COFFEE", ""), ("2024-01-31", "8.00", "LUNCH", ""),
                     ("2024-01-31", "8.00", "LUNCH", "")))
    rep = s.add_file(_file(("2024-01-31", "8.00", "LUNCH", ""), ("2024-01-31", "8.00", "LUNCH", ""),
                           ("2024-01-31", "8.00", "LUNCH", ""), ("2024-02-03", "2.00", "BUS", "")))
    # overlap is 2024-01-31..2024-01-31; two of the three LUNCH rows match existing ones
    assert rep.excluded_overlap == 2
    assert len(s.transactions) == 3 + 2


def test_r_4_3_user_can_keep_overlap():
    s = ImportSession()
    s.add_file(_file(("2024-01-31", "8.00", "LUNCH", "")))
    rep = s.add_file(_file(("2024-01-31", "8.00", "LUNCH", ""), ("2024-02-03", "2.00", "BUS", "")), keep_overlap=True)
    assert rep.excluded_overlap == 0 and len(s.transactions) == 3


def test_r_4_3_other_account_not_matched():
    s = ImportSession()
    s.add_file(_file(("2024-01-31", "8.00", "LUNCH", ""), account="card"))
    rep = s.add_file(_file(("2024-01-31", "8.00", "LUNCH", ""), account="checking"))
    assert rep.excluded_overlap == 0 and len(s.transactions) == 2


def test_r_4_4_same_content_blocked():
    s = ImportSession()
    s.add_file(_file(("2024-01-02", "3.50", "COFFEE", "")))
    with pytest.raises(DuplicateFile):
        s.add_file(_file(("2024-01-02", "3.50", "COFFEE", "")))


def test_r_1_7_generator_is_deterministic_and_purchases_only():
    from roundup_engine.generator import generate_transactions
    a = generate_transactions(seed=7, start="2024-01-01", end="2024-03-31")
    b = generate_transactions(seed=7, start="2024-01-01", end="2024-03-31")
    assert a == b and a
    assert all(t["direction"] == "debit" and t["status"] == "posted" for t in a)
    assert generate_transactions(seed=8, start="2024-01-01", end="2024-03-31") != a


# ---- R-1.4a (OQ-12): free-text statuses from a file ----
import pytest as _pytest  # noqa: E402
from roundup_engine.importing import _status  # noqa: E402


@_pytest.mark.parametrize("text", ["posted", "Posted", "SETTLED", " cleared ", "Completed", "completed  "])
def test_r_1_4a_clearly_posted_words(text):
    assert _status(text, mapped=True) == "posted"


@_pytest.mark.parametrize("text,want", [("pending", "pending"), ("Pending", "pending"), ("cancelled", "cancelled"), ("CANCELED", "cancelled"),
                                         ("void", "cancelled"), ("Voided", "cancelled")])
def test_r_1_4a_pending_and_cancelled_keep_their_own_meaning(text, want):
    assert _status(text, mapped=True) == want


@_pytest.mark.parametrize("text", ["reversed", "returned", "declined", "failed", "on hold", "authorized", "hold", "refunded", "x", ""])
def test_r_1_4a_everything_else_is_unrecognised_when_a_status_column_is_mapped(text):
    assert _status(text, mapped=True) == "unrecognised"


def test_r_1_4a_no_status_column_means_posted():
    assert _status("", mapped=False) == "posted"
