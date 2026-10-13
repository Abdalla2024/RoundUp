"""One error shape for every failure: {"error": {"code", "message", "fields"?}} (API.md)."""

from dataclasses import dataclass, field


@dataclass
class ApiError(Exception):
    status: int
    code: str
    message: str
    fields: list[str] = field(default_factory=list)
    headers: dict = field(default_factory=dict)

    def body(self) -> dict:
        err = {"code": self.code, "message": self.message}
        if self.fields:
            err["fields"] = self.fields
        return {"error": err}


ENGINE_MESSAGES = {
    "WINDOW_OUTSIDE_DATA": "The dates must be inside the scenario's range ({start} to {end}), the start date "
                           "must not be after the end date, and the dates must include at least one trading day.",
    "GAP_TOO_LONG": "The price data has too many missing days in a row, so no result can be given.",
    "GAP_ON_EVENT": "The price data is missing a price on a dividend or split day, so no result can be given.",
    "EVENT_NOT_CALENDAR_DAY": "The price data has a dividend or split on a day the market was closed.",
    "CLOSE_ON_CLOSED_DAY": "The price data has a price on a day the market was closed.",
    "SPLIT_ADJUSTED_SERIES": "The price data looks already adjusted for a split, so it cannot be used.",
    "EX_AFTER_PAY": "The price data has a dividend paid before its ex-dividend date.",
    "MISSING_PAY_DATE": "The price data has a dividend without a payment date.",
}
