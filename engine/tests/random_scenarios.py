"""Deterministic random scenario generator (seeded), used by property tests and the cross-check.

Integer and Decimal arithmetic only. The generated series are valid by construction:
raw prices across splits, at most 3 consecutive missing closes, no gap on event days,
window inside the data. Error behaviour is covered by golden cases, not here.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from builders import scenario

STRATEGIES = ["threshold", "next_session", "weekly", "monthly"]
SPLIT_RATIOS = ["2", "3", "0.5"]


def _cents_str(c: int) -> str:
    return f"{c // 100}.{c % 100:02d}"


def generate(seed: int, n_days: int = 70) -> dict:
    rng = random.Random(seed)
    start_day = date(2024, 1, 1) + timedelta(days=rng.randint(0, 300))
    calendar = []
    day = start_day
    while len(calendar) < n_days:
        if day.weekday() < 5 and rng.randint(1, 25) != 1:  # weekdays, ~4% holidays
            calendar.append(day)
        day += timedelta(days=1)

    # Price walk in integer cents (pre-split basis).
    price = rng.randint(1000, 20000)
    base = {}
    for d in calendar:
        price = max(100, price + rng.randint(-(price // 25), price // 25))
        base[d] = price

    # Optional split (not in the first 3 or last 3 days so P and Q exist).
    splits = []
    factor = Decimal(1)
    split_day = None
    if rng.randint(1, 3) == 1:
        split_day = calendar[rng.randint(3, len(calendar) - 4)]
        ratio = rng.choice(SPLIT_RATIOS)
        splits.append({"ex_date": split_day.isoformat(), "ratio": ratio})
        factor = Decimal(ratio)

    def close_str(d):
        c = Decimal(base[d]) / Decimal(100)
        if split_day is not None and d >= split_day:
            c = c / factor
        return str(c.quantize(Decimal("0.0001")))

    # Dividends (0-3), ex-date on calendar days, pay 0-14 days later.
    dividends = []
    used_ex = set()
    for _ in range(rng.randint(0, 3)):
        ex = calendar[rng.randint(1, len(calendar) - 2)]
        if ex in used_ex:
            continue
        used_ex.add(ex)
        pay = ex + timedelta(days=rng.randint(0, 14))
        per_share_cents = rng.randint(1, max(1, base[ex] // 60))
        amt = Decimal(per_share_cents) / Decimal(100)
        if split_day is not None and ex >= split_day:
            amt = amt / factor
        dividends.append({"ex_date": ex.isoformat(), "pay_date": pay.isoformat(),
                          "amount_raw": str(amt.quantize(Decimal("0.000001")))})

    protected = set(used_ex) | ({split_day} if split_day else set())
    if split_day is not None:
        protected.add(calendar[calendar.index(split_day) - 1])
    protected |= {calendar[0], calendar[-1]}

    # Gaps: a few runs of 1-3 missing closes.
    missing = set()
    for _ in range(rng.randint(0, 3)):
        i = rng.randint(1, len(calendar) - 5)
        for d in calendar[i:i + rng.randint(1, 3)]:
            if d not in protected:
                missing.add(d)
    # Keep runs <= 3 (two runs may merge): drop extra missing days if needed.
    run = 0
    for d in calendar:
        if d in missing:
            run += 1
            if run > 3:
                missing.discard(d)
                run = 0
        else:
            run = 0

    closes = {d.isoformat(): close_str(d) for d in calendar if d not in missing}

    window_start = calendar[rng.randint(0, 5)]
    window_end = calendar[-1 - rng.randint(0, 5)]
    if rng.randint(1, 4) == 1:  # sometimes end on a weekend/holiday after a session
        window_end = min(window_end + timedelta(days=1), calendar[-1])
    # end must not exceed the last close (calendar[-1] always has a close)

    txs = []
    for _ in range(rng.randint(0, 60)):
        d = window_start + timedelta(days=rng.randint(-3, (window_end - window_start).days + 3))
        r = rng.randint(1, 100)
        amount = _cents_str(rng.randint(1, 9999))
        if r <= 2:
            amount = "1.234"
        direction = "credit" if 3 <= r <= 12 else "debit"
        status = "pending" if 13 <= r <= 17 else ("cancelled" if r == 18 else "posted")
        desc = "ATM WITHDRAWAL" if 19 <= r <= 21 else ("COFFEE" if r % 2 else "GROCERY")
        txs.append({"posted_date": d.isoformat(), "amount": amount, "direction": direction,
                    "status": status, "type": "", "description": desc})

    return scenario(f"R-{seed:04d}", [d.isoformat() for d in calendar], closes, txs,
                    rng.choice(STRATEGIES), window_start.isoformat(), window_end.isoformat(),
                    reinvest=rng.randint(0, 3) != 0, dividends=dividends, splits=splits,
                    description=f"random scenario seed {seed}")
