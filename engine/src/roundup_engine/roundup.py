"""Round-up definition (FINANCE-RULES §2)."""


def roundup_cents(amount_cents: int) -> int:
    """R-2.1/R-2.2: spare change to the next whole dollar; whole-dollar purchases round up 0."""
    if not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
        raise TypeError("amount must be integer cents")
    if amount_cents <= 0:
        raise ValueError("round-ups apply only to positive purchase amounts")
    return (100 - amount_cents % 100) % 100
