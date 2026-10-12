# Independent cross-check implementation

`crosscheck.py` is a second, deliberately naive implementation of the simulation. It uses exact
`fractions.Fraction` arithmetic and only the standard library.

**Provenance.** It was written by a separate AI agent session that could see **only**
`FINANCE-RULES.md`, `engine/fixtures/FORMAT.md`, and later the scenario input files. It never saw the
engine source, the golden expectations, or any engine output. Its record of interpretation choices is
`AMBIGUITIES.md`. Several of those entries (AMB-1, 4, 7, 17, 18) led to spec clarifications.

- Self-test (the author's own hand-computed cases): `python3 -I selftest/run_selftest.py`
- Run on scenarios: `python3 -I crosscheck.py ../engine/fixtures/scenarios/*.json`
- Agreement with the engine is enforced by `engine/tests/test_crosscheck.py`.

Do not "fix" this implementation to match the engine. A disagreement is resolved by going back to
the rule text (TEST-STRATEGY.md §4).
