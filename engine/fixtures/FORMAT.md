# Scenario fixture format and result format

Each file in `fixtures/scenarios/` is one JSON scenario, a single-fund run (FINANCE-RULES R-5.7). **Every number is a JSON string**, never a JSON number, so no implementation ever parses a float (R-0.5). Dates are `YYYY-MM-DD`.

## Input

```json
{
  "id": "G-11",
  "description": "free text",
  "covers": ["R-5.1"],
  "market": {
    "symbol": "TEST",
    "calendar": ["2024-01-02", "2024-01-03"],
    "closes": {"2024-01-02": "50.00", "2024-01-03": "51.25"},
    "dividends": [{"ex_date": "2024-01-03", "pay_date": "2024-01-05", "amount_raw": "0.50"}],
    "splits": [{"ex_date": "2024-01-03", "ratio": "3"}]
  },
  "transactions": [
    {"posted_date": "2024-01-02", "amount": "4.37", "direction": "debit",
     "status": "posted", "type": "", "description": "COFFEE SHOP"}
  ],
  "config": {"strategy": "threshold", "start": "2024-01-02", "end": "2024-01-31", "reinvest": "true"}
}
```

- `calendar`: every **calendar-open day** (R-5.6) in the data. Days not listed are closed.
- `closes`: raw closing price per day. A calendar-open day with no entry is a **data gap** (R-6.2).
- `dividends[].pay_date` may be `null` (tests R-8.8).
- `splits[].ratio` = new shares ÷ old shares (R-7.4).
- `transactions[].amount`: a positive decimal string with up to 2 decimal places. Strings with more than 2 decimals, or that are not numbers, are invalid (R-0.1). `direction` is `debit` or `credit`. `status` is `posted`, `pending` or `cancelled`. `type` may be empty.
- `config.strategy` is one of `threshold`, `next_session`, `weekly`, `monthly`. The threshold is fixed at $5.00. `reinvest` is `"true"` or `"false"`.

## Output

```json
{
  "status": "ok",
  "error_code": null,
  "summary": {
    "contributed": "12.34",
    "roundup_buys": "3",
    "dividend_buys": "1",
    "dividends_earned": "1.23",
    "dividends_paid": "1.23",
    "shares": "1.234567",
    "holdings_value": "62.10",
    "uninvested_cash": "0.47",
    "receivables": "0.00",
    "ending_value": "62.57",
    "gain": "50.23",
    "gain_pct": "407.05",
    "as_of": "2024-01-31"
  },
  "buys": [
    {"date": "2024-01-03", "kind": "roundup", "cash": "5.12", "price": "51.25",
     "shares": "0.099902", "delayed_by_data_gap": "false"}
  ],
  "series": [{"date": "2024-01-02", "value": "0.63", "carried": "false"}],
  "transactions_used": "7",
  "transactions_ignored": "2"
}
```

- Money values: exact value rounded to cents, `ROUND_HALF_EVEN`. Shares: 6 decimal places, `ROUND_HALF_EVEN`. `gain_pct`: 2 decimal places, `ROUND_HALF_EVEN`, or `"n/a"` when contributed is 0 (R-0.4, R-13.1).
- `price` is the close used, exactly as given in the input.
- `as_of` is the date of the last close on or before `end` (R-12.3).
- `buys` are in execution order. On the same day, round-up batches come first in cut-off order, then dividend reinvestments in ex-date order.
- `series` has one point per calendar-open day in [start, end] (R-13.2).
- `transactions_used` counts rows that produced a round-up candidate: posted purchase debits inside the window, including whole-dollar ones that round up $0. `transactions_ignored` counts every other row.
- When the run fails, `status` is `"error"`, `error_code` is set, and `summary`, `buys` and `series` are `null`.

### Error codes

| Code | Rule |
|---|---|
| `WINDOW_OUTSIDE_DATA` | R-12.1 (start before first close, end after last close, or start > end) |
| `GAP_TOO_LONG` | R-6.3(a) |
| `GAP_ON_EVENT` | R-6.3(b) |
| `EVENT_NOT_CALENDAR_DAY` | R-6.3(c): split/dividend ex-date not a calendar-open day |
| `CLOSE_ON_CLOSED_DAY` | R-6.3(c): a close dated on a day not in `calendar` |
| `SPLIT_ADJUSTED_SERIES` | R-7.5 |
| `EX_AFTER_PAY` | R-8.7 |
| `MISSING_PAY_DATE` | R-8.8 |

Series validation (R-6.3(c), R-7.5, R-8.7, R-8.8) covers the **whole** market input. Gap rules (R-6.3(a)(b)) apply only inside the window. If several errors apply, report the first in this order: `WINDOW_OUTSIDE_DATA`, `CLOSE_ON_CLOSED_DAY`, `EVENT_NOT_CALENDAR_DAY`, `MISSING_PAY_DATE`, `EX_AFTER_PAY`, `SPLIT_ADJUSTED_SERIES`, `GAP_ON_EVENT`, `GAP_TOO_LONG`.
