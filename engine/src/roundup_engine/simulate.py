"""The simulation: one fund, one strategy (FINANCE-RULES §5-§13)."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, localcontext

from .market import DataError, MarketSeries, validate_series
from .money import CONTEXT, cents_to_decimal
from .roundup import roundup_cents
from .strategies import make_batches
from .transactions import Transaction, select_purchases

MAX_GAP_RUN = 3   # R-6.3(a): 4 or more consecutive missing closes fails


@dataclass(frozen=True)
class Config:
    strategy: str
    start: date
    end: date
    reinvest: bool = True


@dataclass(frozen=True)
class Buy:
    date: date
    kind: str                      # "roundup" | "dividend"
    cash: Decimal
    price: Decimal
    shares: Decimal
    delayed_by_data_gap: bool
    cutoff: date | None = None     # round-up batches
    purchase_dates: tuple[date, ...] = ()
    pay_date: date | None = None   # dividend reinvestments

    @property
    def cash_cents(self) -> int:
        return int(self.cash * 100)  # exact for round-up batches (whole cents)


@dataclass(frozen=True)
class Point:
    date: date
    value: Decimal
    carried: bool


@dataclass
class _Earned:
    ex_date: date
    pay_date: date
    amount: Decimal
    reinvest_on: date | None
    delayed: bool
    reinvested: bool = False


@dataclass(frozen=True)
class RunResult:
    as_of: date
    last_price: Decimal
    contributed_cents: int
    roundup_uninvested_cents: int
    dividend_cash: Decimal
    receivables: Decimal
    shares: Decimal
    holdings_value: Decimal
    uninvested_cash: Decimal
    ending_value: Decimal
    dividends_earned: Decimal
    dividends_paid: Decimal
    buys: tuple[Buy, ...]
    series: tuple[Point, ...]
    used: tuple[Transaction, ...]
    ignored: tuple[tuple[int, str], ...]
    market_checksum: str = field(default="")

    @property
    def gain(self) -> Decimal:
        with localcontext(CONTEXT):
            return self.ending_value - cents_to_decimal(self.contributed_cents)

    @property
    def gain_pct(self) -> Decimal | None:
        if self.contributed_cents == 0:
            return None
        with localcontext(CONTEXT):
            return self.gain / cents_to_decimal(self.contributed_cents) * 100


def _first_after(days, after: date, inclusive: bool):
    for d in days:
        if d > after or (inclusive and d == after):
            return d
    return None


def simulate(market: MarketSeries, rows: list[dict], config: Config) -> RunResult:
    with localcontext(CONTEXT):
        return _simulate(market, rows, config)


def _simulate(m: MarketSeries, rows, cfg: Config) -> RunResult:
    # ---- validation, in FORMAT.md precedence order
    if m.first_close is None or cfg.start > cfg.end or cfg.start < m.first_close or cfg.end > m.data_end:
        raise DataError("WINDOW_OUTSIDE_DATA")                                        # R-12.1
    validate_series(m)
    window_days = [d for d in m.calendar if cfg.start <= d <= cfg.end]
    run = 0
    for d in window_days:                                                             # R-6.3(a)
        run = run + 1 if d not in m.closes else 0
        if run > MAX_GAP_RUN:
            raise DataError("GAP_TOO_LONG", d.isoformat())

    # ---- transactions and batches
    used, ignored = select_purchases(rows, cfg.start, cfg.end)
    roundups = [(t.date, roundup_cents(t.amount_cents)) for t in used]
    contributed = sum(c for _, c in roundups)
    batches, _ = make_batches(roundups, cfg.strategy)

    sessions = [d for d in m.calendar if d in m.closes]
    plan: dict[date, list] = {}            # execution day -> batches, in cut-off order
    for b in batches:
        ex = _first_after(sessions, b.cutoff, inclusive=False)                        # R-5.1
        if ex is not None and ex <= cfg.end:                                          # R-5.4
            first_open = _first_after(m.calendar, b.cutoff, inclusive=False)
            plan.setdefault(ex, []).append((b, first_open != ex))                     # R-6.2 flag

    splits = {s.ex_date: s for s in m.splits}
    divs = sorted(m.dividends, key=lambda x: x.ex_date)
    roundup_by_day: dict[date, int] = {}
    for day, c in roundups:
        roundup_by_day[day] = roundup_by_day.get(day, 0) + c

    shares = Decimal(0)
    bought_cents = 0
    earned: list[_Earned] = []
    buys: list[Buy] = []
    series: list[Point] = []
    last_day = m.last_close_on_or_before(cfg.start)
    last_price = m.closes[last_day]

    def cash_and_receivables(asof: date):
        rcash = sum(c for d, c in roundup_by_day.items() if d <= asof) - bought_cents
        dcash = sum((e.amount for e in earned if e.pay_date <= asof and not e.reinvested), Decimal(0))
        recv = sum((e.amount for e in earned if e.pay_date > asof), Decimal(0))
        return rcash, dcash, recv

    for d in window_days:
        if d in m.closes:
            price = m.closes[d]
            last_price, last_day = price, d
            if d in splits:                                                            # R-8.1 (1)
                shares *= splits[d].ratio
            for x in divs:                                                             # R-8.1 (2), R-8.2/8.3
                if x.ex_date == d and shares > 0:
                    reinvest_on = _first_after(sessions, x.pay_date, inclusive=True)
                    first_open = _first_after(m.calendar, x.pay_date, inclusive=True)
                    earned.append(_Earned(d, x.pay_date, shares * x.amount, reinvest_on,
                                          first_open is not None and first_open != reinvest_on))
            for b, delayed in plan.get(d, []):                                         # R-8.1 (3) round-ups
                cash = cents_to_decimal(b.cents)
                got = cash / price
                shares += got
                bought_cents += b.cents
                buys.append(Buy(d, "roundup", cash, price, got, delayed, b.cutoff, b.purchase_dates))
            if cfg.reinvest:                                                           # R-8.5
                for e in earned:
                    if not e.reinvested and e.reinvest_on == d:
                        got = e.amount / price
                        shares += got
                        e.reinvested = True
                        buys.append(Buy(d, "dividend", e.amount, price, got, e.delayed, pay_date=e.pay_date))
            carried = False
        else:
            carried = True                                                             # R-6.4
        rcash, dcash, recv = cash_and_receivables(d)
        series.append(Point(d, shares * last_price + cents_to_decimal(rcash) + dcash + recv, carried))

    # ---- summary as of the end date (R-13.1)
    rcash, dcash, recv = cash_and_receivables(cfg.end)
    as_of = m.last_close_on_or_before(cfg.end)
    holdings = shares * last_price
    uninvested = cents_to_decimal(rcash) + dcash
    return RunResult(
        as_of=as_of, last_price=last_price, contributed_cents=contributed, roundup_uninvested_cents=rcash,
        dividend_cash=dcash, receivables=recv, shares=shares, holdings_value=holdings,
        uninvested_cash=uninvested, ending_value=holdings + uninvested + recv,
        dividends_earned=sum((e.amount for e in earned), Decimal(0)),
        dividends_paid=sum((e.amount for e in earned if e.pay_date <= cfg.end), Decimal(0)),
        buys=tuple(buys), series=tuple(series), used=tuple(used), ignored=tuple(ignored),
        market_checksum=m.checksum(),
    )
