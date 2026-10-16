# Synthetic market scenarios: model and parameters

The shared demo runs on **named synthetic market scenarios**, not real funds (OPEN-QUESTIONS D-7, as amended by the owner). Each scenario is produced by the seeded model below, so anyone can regenerate it exactly. The code is in `engine/src/roundup_scenarios/`.

**Every scenario carries this label wherever it is shown:**

> **Synthetic scenario. Not a real fund, not real prices, and not a forecast.**

Scenarios are illustrations of *kinds* of market behaviour, chosen to show how round-ups, timing, dividends and splits interact. They make no claim about any real market, past or future.

## Model (version `scenario-model-2`)

All arithmetic is integer basis points and `Decimal` (no floats, FINANCE-RULES R-0.5). Randomness comes from Python's `random.Random`, seeded with the string `"<family>:<style>:<seed>"`, which is deterministic across runs and platforms. Only integer draws (`randint`) are used.

**Calendar.** Weekdays from 2012-01-03 to 2026-09-30, minus the NYSE's regular holidays computed by rule:
- New Year's Day: Jan 1; if Sunday, then Monday; if Saturday, none.
- Martin Luther King Jr. Day: 3rd Monday of January.
- Washington's Birthday: 3rd Monday of February.
- Good Friday.
- Memorial Day: last Monday of May.
- Juneteenth: from 2022.
- Independence Day.
- Labor Day: 1st Monday of September.
- Thanksgiving: 4th Thursday of November.
- Christmas.

Juneteenth, Independence Day and Christmas move to Friday when they fall on a Saturday and to Monday when they fall on a Sunday. The 2026 dates are tested against the NYSE holiday page. Unscheduled closures (e.g. Hurricane Sandy, national days of mourning) are **not** modelled. This is a synthetic calendar, not an official one.

**Daily return** (basis points) on session *t*: `r = drift + pull + shock`.
- `shock = round_half_even(vol × Z / 1000)`.
- `Z` = (sum of 12 draws of `randint(0, 1000)`) − 6000. This is an Irwin–Hall approximation of a normal draw with standard deviation ≈ 1000.
- `pull` is `0` unless the family sets a **reversion** (only `sideways` does). Then `pull = −round_half_even(gap_bp × reversion ÷ 1000)`, where `gap_bp` is how far one share held from day one (the close times the split ratios so far) sits above (+) or below (−) its starting price, in basis points, rounded half-even. It closes `reversion` per mille of that gap each day, so the series wanders but is drawn back. It draws no extra random numbers.
- `r` is clamped to [−2500, +2500] bp (±25%) on normal days and [−500, +500] bp on a split's ex-date. The narrow clamp keeps the engine's split-basis check (R-7.5) unambiguous.

**Price.** `close_t = close_{t−1} × (10000 + r) / 10000`, rounded half-even to 4 decimal places, with a floor of 0.0100 (so prices stay positive).
- On a dividend ex-date, the dividend amount is subtracted from that close.
- On a split ex-date, the close is divided by the split ratio.
- Prices are **raw** (R-7.1): never adjusted afterwards.

**Dividends.** Quarterly.
- **Ex-date:** the first session on or after the 15th of March, June, September and December.
- **Pay date:** ex-date + 7 calendar days. This may fall on a weekend or holiday, which is allowed (FORMAT.md, AMB-17).
- **Amount per share:** `close_{ex−1} × yield_bp / 40000`, rounded half-even to 4 decimal places. It is on the raw basis of the ex-date (R-7.4).

**Split.** Exactly one per series.
- **Ex-date:** a seeded session between 40% and 60% of the way through the calendar, never on a dividend ex-date or the session before one.
- **Ratio:** fixed per family (below).

**Regimes.** Each family is a list of regimes `(starts at fraction of sessions, drift bp/day, vol bp)`. The dividend style subtracts 1 bp/day of drift, because a fund paying more out in dividends grows its price a little more slowly.

## Families (one per scenario) and styles

| Scenario id | Name | Regimes (from, drift, vol) | Split ratio | Published seed |
|---|---|---|---|---|
| `steady-growth` | Steady growth | (0, +4, 70) | 3 (3-for-1) | 1101 |
| `crash-and-recovery` | Crash and recovery | (0, +3, 80), (0.30, −45, 260), (0.335, +12, 140), (0.55, +3, 80) | 0.5 (1-for-2 reverse) | 1202 |
| `sideways` | Sideways | (0, 0, 70), reversion 12 per mille | 2 (2-for-1) | 1303 |
| `high-volatility` | High volatility | (0, +3, 230) | 2 (2-for-1) | 1404 |

| Style | Starting price | Dividend yield | Drift adjustment | Shown as |
|---|---|---|---|---|
| `broad` | 100.0000 | 150 bp/yr (1.5%) | 0 | "Broad-market style (synthetic)" |
| `dividend` | 40.0000 | 350 bp/yr (3.5%) | −1 bp/day | "Dividend style (synthetic)" |

Symbols are `SYN-<FAMILY>-<STYLE>`, e.g. `SYN-STEADY-GROWTH-BROAD`. They never resemble real tickers. A test checks every name, label, description and symbol against a list of real ticker symbols.

The parameters are illustrative. For example, +4 bp/day compounds to roughly 10% a year before dividends. They were chosen so the families look visibly different over 2012–2026. They are not estimates of anything.

## Sideways: the stated band (version 2, owner decision OQ-15, 2026-10-16)

In version 1, "Sideways" had zero drift and 90 bp of daily noise and nothing holding it near its start, so a random walk could end anywhere: the published broad-market series ended at 0.31 of its starting value, which is not "no overall trend". Version 2 keeps the zero drift, lowers the daily noise to 70 bp and adds the reversion above (12 per mille of the gap per day, a half-life of about 58 sessions; with this noise it gives a typical swing of about ±6%). The reversion is a model choice for illustration, not an estimate of anything.

The band the model must stay inside (enforced by `engine/tests/test_sideways_band.py`, for both styles, for the published seed **and** for seeds 1 to 60, so it is the model and not a lucky seed). "Level" is what one share held from the first day is worth (the close times the split ratios so far; dividends are not added back):
- the final level is within 15% of the start;
- the whole path stays between 0.75 and 1.30 times the start;
- the largest fall from a peak to a later low (maximum drawdown) is at most 30%.

Measured: published broad-market series ends at 0.913 of its start (lowest 0.855, highest 1.138, largest fall 23.0%); published dividend series ends at 0.918 (0.875, 1.178, 22.8%). Across seeds 1 to 60: worst final distance from the start 12.3%, lowest level 0.772, highest 1.208, largest fall 29.4%. The ending is a little below the start because the dividends paid out of the share price are not added back. The other six published series are byte-for-byte unchanged (their checksums are pinned in `engine/tests/test_sideways_band.py::test_other_scenarios_are_unchanged`).

## Changing the model

Any change to a parameter or rule bumps `MODEL_VERSION`. Saved results record the scenario id, seed, model version and market checksum (R-12.4), so a re-run can say that the scenario changed.
