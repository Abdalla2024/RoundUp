"""Fast guards for the two requirements files (the full fresh-venv install is tools/check_requirements.py, run first in CI)."""

import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_requirements", ROOT / "tools" / "check_requirements.py")
chk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chk)


def test_ci_file_is_derived_from_the_vercel_file():
    assert (ROOT / "requirements-ci.txt").read_text() == chk.derive((ROOT / "requirements.txt").read_text())


def test_the_vercel_file_keeps_the_lines_that_built_on_vercel():
    lines = (ROOT / "requirements.txt").read_text().splitlines()
    assert all(l in lines for l in chk.VERCEL_LINES)
    assert not any(l.startswith("./") for l in lines)


def test_pip_accepts_the_ci_file_and_rejects_the_vercel_form(tmp_path):
    """Negative control: the failing form from the CI run (38765010785) must be seen as a failure by this check."""
    ok, out = chk.pip_accepts([ROOT / "requirements-ci.txt"])
    assert ok, out
    bad = tmp_path / "bad.txt"
    bad.write_text("roundup-engine @ ./engine\n")
    ok, out = chk.pip_accepts([bad])
    assert not ok and "Invalid URL" in out, out


def test_same_third_party_pins_in_both_files():
    pins = lambda p: [l for l in (ROOT / p).read_text().splitlines() if "==" in l]
    assert pins("requirements.txt") == pins("requirements-ci.txt")
