# roundup_engine

The RoundUp simulation engine: a pure Python library with no I/O, no network and no dependencies.
Money is integer cents; everything derived is `Decimal` (precision 28, half-even, `FloatOperation`
trapped). Rules: [FINANCE-RULES.md](../FINANCE-RULES.md). Input and output format:
[fixtures/FORMAT.md](fixtures/FORMAT.md).

```bash
# setup: see the root README.md (one environment for engine, API and tests)
.venv/bin/pytest -q                       # from engine/: golden, property, import, cross-check agreement, no-floats
.venv/bin/python tools/fault_injection.py # break each rule in a scratch copy; every mutation must be caught
.venv/bin/python tools/export_fixtures.py # regenerate fixtures/scenarios (inputs only)
```

```python
from roundup_engine import run_scenario   # scenario dict (FORMAT.md) -> result dict
```

| Module | Rules |
|---|---|
| `money.py` | R-0.x parsing, context, display rounding |
| `roundup.py` | R-2.x |
| `transactions.py` | R-1.4–R-1.8, R-3.2 (which rows round up) |
| `importing.py` | R-1.2, R-1.3, R-4.x (CSV rows → transactions, duplicates) |
| `market.py` | R-6.3, R-7.5, R-8.7, R-8.8 (series validation) |
| `strategies.py` | R-5.1, R-5.2 (batching) |
| `simulate.py` | R-5–R-13 (day loop, dividends, splits, results) |
| `scenario.py` | FORMAT.md adapter |
| `generator.py` | R-1.7 seeded sample transactions |
