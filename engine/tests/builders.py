"""Helpers for building scenario dicts in the fixtures/FORMAT.md shape."""

from datetime import date, timedelta


def d(s: str) -> date:
    return date.fromisoformat(s)


def weekdays(start: str, end: str, closed=()) -> list[str]:
    """Calendar-open days: Mon-Fri in [start, end] minus `closed`."""
    out, day, stop = [], d(start), d(end)
    closed = set(closed)
    while day <= stop:
        if day.weekday() < 5 and day.isoformat() not in closed:
            out.append(day.isoformat())
        day += timedelta(days=1)
    return out


def closes(calendar, path, missing=()) -> dict[str, str]:
    """`path` is a list of (first_day, price) steps; each price holds until the next step."""
    steps = sorted(path)
    out = {}
    for day in calendar:
        if day in missing:
            continue
        price = None
        for first, p in steps:
            if day >= first:
                price = p
        if price is not None:
            out[day] = price
    return out


def tx(day, amount, direction="debit", status="posted", type_="", desc="SHOP"):
    return {"posted_date": day, "amount": amount, "direction": direction,
            "status": status, "type": type_, "description": desc}


def repeat(day, amount, n, desc="SHOP"):
    return [tx(day, amount, desc=desc) for _ in range(n)]


def scenario(sid, calendar, closes_, txs, strategy, start, end, reinvest=True,
             dividends=(), splits=(), description="", covers=()):
    return {
        "id": sid,
        "description": description,
        "covers": list(covers),
        "market": {"symbol": "TEST", "calendar": list(calendar), "closes": dict(closes_),
                   "dividends": [dict(x) for x in dividends], "splits": [dict(x) for x in splits]},
        "transactions": list(txs),
        "config": {"strategy": strategy, "start": start, "end": end,
                   "reinvest": "true" if reinvest else "false"},
    }


def div(ex, pay, amount):
    return {"ex_date": ex, "pay_date": pay, "amount_raw": amount}


def split(ex, ratio):
    return {"ex_date": ex, "ratio": ratio}
