"""RoundUp simulation engine: a pure library (no I/O, no network), Decimal and integer cents only."""

ENGINE_VERSION = "0.1.0"

from .scenario import run_scenario  # noqa: E402

__all__ = ["ENGINE_VERSION", "run_scenario"]
