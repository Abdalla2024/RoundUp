"""Write scenario fixtures (inputs only, no expectations) for the independent cross-check.

    python tools/export_fixtures.py [n_random]
"""

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(HERE / "tests"), str(HERE / "src")]

from golden_cases import CASES  # noqa: E402
from random_scenarios import generate  # noqa: E402

OUT = HERE / "fixtures" / "scenarios"


def main(n_random: int = 30) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    scenarios = [c["scenario"] for c in CASES] + [generate(seed) for seed in range(1000, 1000 + n_random)]
    for s in scenarios:
        (OUT / f"{s['id']}.json").write_text(json.dumps(s, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(scenarios)} scenarios to {OUT}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
