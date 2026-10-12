"""Seeded synthetic transactions (R-1.7): always posted purchases, integer cents."""

import random
from datetime import date, timedelta

MERCHANTS = ("COFFEE SHOP", "GROCERY", "BOOKSTORE", "BAKERY", "PHARMACY", "CINEMA", "LUNCH SPOT", "HARDWARE")


def generate_transactions(seed: int, start: str, end: str, max_per_day: int = 3) -> list[dict]:
    rng = random.Random(seed)
    day, stop = date.fromisoformat(start), date.fromisoformat(end)
    out = []
    while day <= stop:
        for _ in range(rng.randint(0, max_per_day)):
            cents = rng.randint(100, 4999)
            out.append({"posted_date": day.isoformat(), "amount": f"{cents // 100}.{cents % 100:02d}",
                        "direction": "debit", "status": "posted", "type": "",
                        "description": rng.choice(MERCHANTS)})
        day += timedelta(days=1)
    return out
