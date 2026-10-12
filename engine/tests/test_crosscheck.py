"""The engine must agree exactly (at display precision) with the independent implementation."""

import importlib.util
import json
import pathlib

import pytest
from random_scenarios import generate

from roundup_engine import run_scenario

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("crosscheck", ROOT / "crosscheck" / "crosscheck.py")
crosscheck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crosscheck)

FIXTURES = sorted((ROOT / "engine" / "fixtures" / "scenarios").glob("*.json"))


def _strip(d):
    return {k: v for k, v in d.items() if k != "engine_version"}


@pytest.mark.parametrize("path", FIXTURES, ids=[p.stem for p in FIXTURES])
def test_fixture_agrees(path):
    s = json.loads(path.read_text())
    assert _strip(run_scenario(s)) == _strip(crosscheck.run(s))


@pytest.mark.parametrize("seed", list(range(9000, 9100)) + [5288])
def test_random_agrees(seed):
    s = generate(seed, n_days=40 + seed % 60)
    assert _strip(run_scenario(s)) == _strip(crosscheck.run(s))
