"""Sparkline shapes of the published scenarios (stage 6, display only): 40 whole numbers from 0 to 100, split-adjusted, from the model itself."""

import pytest

from roundup_scenarios import FAMILIES, STYLES, get_published
from roundup_scenarios.model import shape

POINTS = 40


def sh(family, style="broad"):
    return shape(get_published(family, style))


@pytest.mark.parametrize("family", list(FAMILIES))
@pytest.mark.parametrize("style", list(STYLES))
def test_every_published_scenario_has_a_full_range_integer_shape(family, style):
    s = sh(family, style)
    assert len(s) == POINTS and all(isinstance(x, int) and 0 <= x <= 100 for x in s)
    assert s == sh(family, style)                            # deterministic


def test_all_scenarios_share_one_scale_so_the_extremes_are_0_and_100_across_the_set():
    every = [x for f in FAMILIES for st in STYLES for x in sh(f, st)]
    assert min(every) == 0 and max(every) == 100


def test_steady_growth_rises():
    s = sh("steady-growth")
    assert s[-1] >= s[0] + 20                                # ends 3.2x its start on a shared log scale
    q = POINTS // 4
    assert sum(s[-q:]) / q > sum(s[:q]) / q + 15            # the last quarter sits well above the first quarter


def test_crash_and_recovery_falls_then_recovers():
    s = sh("crash-and-recovery")
    trough = s.index(min(s))
    assert 3 <= trough <= POINTS - 4                         # the low point is in the middle, not at either end
    assert max(s[:trough]) - s[trough] >= 8                  # a visible fall before it, on the shared scale
    assert s[-1] - s[trough] >= 8                            # and a visible recovery after it


def test_high_volatility_is_rougher_than_steady_growth():
    rough = lambda s: sum(abs(a - b) for a, b in zip(s, s[1:]))
    assert rough(sh("high-volatility")) > 1.5 * rough(sh("steady-growth"))


# Not asserted, on purpose: that "sideways" has no overall trend. The published seeded series for sideways/broad ends at 0.31 of its
# starting value (found when the shape was first drawn on a shared scale); that is a property of the published model and its seed, reported
# to the owner (OPEN-QUESTIONS OQ-14), not something to hide by normalising each picture to its own height.
