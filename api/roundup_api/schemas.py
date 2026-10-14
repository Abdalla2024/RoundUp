"""Strict request schemas: unknown fields rejected, no type coercion (Pydantic strict mode, extra='forbid')."""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DATE = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"            # ASCII digits only (\d matches any Unicode digit)
AMOUNT = r"^[0-9]{1,7}(\.[0-9]{1,2})?$"
MAX_TRANSACTIONS = 20_000


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def _real_date(v: str) -> str:
    date.fromisoformat(v)          # raises ValueError for e.g. 2015-02-30
    return v


class TransactionIn(Strict):
    posted_date: str = Field(pattern=DATE)
    amount: str = Field(pattern=AMOUNT)
    direction: Literal["debit", "credit"]
    status: Literal["posted", "pending", "cancelled", "unrecognised"] = "posted"
    category: Optional[Literal["purchase", "non_purchase"]] = None
    description: Optional[str] = Field(default=None, max_length=140)

    _d = field_validator("posted_date")(_real_date)


class GenerateIn(Strict):
    seed: int = Field(ge=0, le=2_147_483_647)
    max_per_day: int = Field(ge=1, le=3)


class RunOptions(Strict):
    scenario_id: str = Field(max_length=64)
    style: str = Field(max_length=32)
    start: str = Field(pattern=DATE)
    end: str = Field(pattern=DATE)
    transactions: Optional[list[TransactionIn]] = Field(default=None, min_length=1, max_length=MAX_TRANSACTIONS)
    generate: Optional[GenerateIn] = None
    buys: Literal["all", "none"] = "all"           # "none": leave the buy list out (counts stay in the summary)

    _s = field_validator("start", "end")(_real_date)

    @model_validator(mode="after")
    def _one_source(self):
        if (self.transactions is None) == (self.generate is None):
            raise ValueError("give either transactions or generate, not both or neither")
        return self


Strategy = Literal["threshold", "next_session", "weekly", "monthly"]


class SimulateIn(RunOptions):
    strategy: Strategy
    reinvest: bool


class Side(Strict):
    strategy: Strategy
    reinvest: bool


class CompareIn(RunOptions):
    a: Side
    b: Side


class SaveIn(SimulateIn):
    name: str = Field(min_length=1, max_length=80)
    save_transactions: bool


class MappingIn(Strict):
    date: Optional[str] = Field(default=None, max_length=100)
    posted_date: Optional[str] = Field(default=None, max_length=100)
    amount: Optional[str] = Field(default=None, max_length=100)
    debit: Optional[str] = Field(default=None, max_length=100)
    credit: Optional[str] = Field(default=None, max_length=100)
    type: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=100)
    external_id: Optional[str] = Field(default=None, max_length=100)
    account: Optional[str] = Field(default=None, max_length=100)


class ParseIn(Strict):
    csv: str = Field(max_length=2_000_000)
    mapping: MappingIn
    sign_convention: Optional[Literal["separate_columns", "type_column", "debits_positive", "debits_negative"]] = None
