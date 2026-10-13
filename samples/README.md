# Sample bank exports

Three small, made-up bank exports for trying the **Upload a CSV** flow, plus the numbers a correct app must show for them. Nothing here is real: the ordinary rows come from the engine's own seeded purchase generator, and the special rows are written out by hand in `make_samples.py`.

Rebuild or check them (they are reproducible, so the check passes only if the files match the script):

```bash
PYTHONPATH=engine/src .venv/bin/python samples/make_samples.py           # rewrite
PYTHONPATH=engine/src .venv/bin/python samples/make_samples.py --check   # verify
```

## The files

| File | Layout | What to choose in the app |
|---|---|---|
| `sample-transactions.csv` | `Date, Description, Amount, Status`. One signed amount column: purchases are positive, refunds are negative | Date → Date, Amount → Amount, Description → Description, Status → Status. Signing: **Purchases are positive numbers** |
| `sample-split-columns.csv` | `Date, Description, Money out, Money in, Status` | Signing: **Separate columns for money out and money in** (the app should pick this for you and say so) |
| `sample-type-column.csv` | `Date, Description, Amount, Type, Status`. `Type` says `debit` or `credit` | Signing: **A column says debit or credit** (the app should pick this for you and say so) |

All three hold the same 92 transactions, dated 2024-01-02 to 2024-03-29. Use the dates 2024-01-02 to 2024-03-29 in step 4 (the scenario runs 2012 to 2026, so any scenario works).

## Which rows count, and which do not

| Kind | Rows | Counted as a purchase? | Why |
|---|---|---|---|
| Ordinary card purchases (posted) | 85 | **Yes** | They round up to the next dollar (R-2.1) |
| A whole-dollar purchase (`Hardware Store`, 20.00, 2024-02-06) | 1 | **Yes, but it adds $0.00** | An exact-dollar amount has no spare change (R-2.2) |
| Refunds (`Bookshop refund` -12.50 on 2024-01-09, `Online shop refund` -8.99 on 2024-03-04) | 2 | **No** | Money coming in never adds a round-up and never takes one away (R-1.8) |
| A transfer (`Transfer to savings`, 200.00) | 1 | **No** | Not a purchase: the description contains the whole word "transfer" (R-1.4) |
| A card payment (`Card payment`, 500.00) | 1 | **No** | Not a purchase: the description contains the whole word "payment" (R-1.4) |
| A pending row (`Maple Grocery`, 31.40, status `pending`) | 1 | **No** | Only posted rows count (R-1.4) |
| A cancelled row (`Bakery`, 4.57, status `cancelled`) | 1 | **No** | Cancelled rows never count (R-3.2) |

## Numbers the app must show (also in `expected.json`)

- **Check step:** 92 of 92 rows can be used; 2 are not purchases (transfer and payment); 2 are money coming in; 2 are pending or cancelled; 1 purchase has a whole-dollar amount.
- **Results, with the window above:** 86 purchases used (85 ordinary + the whole-dollar one), 6 rows ignored (2 refunds, transfer, payment, pending, cancelled), **$38.70** of round-ups added. That total is worked out in `make_samples.py` with plain integer arithmetic on cents, independently of the parser and the engine.

If you change the generator seed, the window or the special rows in `make_samples.py`, run it again and commit the new files and `expected.json` together.
