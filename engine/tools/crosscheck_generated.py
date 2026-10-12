"""Cross-check the engine against the independent implementation on generated scenario series.

    python tools/crosscheck_generated.py [n_seeds_per_series]

For each family x style x seed: random window (sometimes the full 2012-2026 range), random strategy,
random reinvest, seeded transactions (incl. non-purchases). Reports every difference.
"""

import importlib.util
import pathlib
import random
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(HERE / "src"), str(HERE / "tools")]

from compare_crosscheck import diff  # noqa: E402
from roundup_engine import run_scenario  # noqa: E402
from roundup_engine.generator import generate_transactions  # noqa: E402
from roundup_scenarios import FAMILIES, STYLES, generate_series, market_dict  # noqa: E402

_spec = importlib.util.spec_from_file_location("crosscheck", HERE.parent / "crosscheck" / "crosscheck.py")
crosscheck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crosscheck)


def scenarios(n_seeds: int):
    for family in FAMILIES:
        for style in STYLES:
            for k in range(n_seeds):
                seed = 50000 + k
                rng = random.Random(f"xc:{family}:{style}:{seed}")
                m = market_dict(generate_series(family, style, seed))
                cal = m["calendar"]
                if k % 5 == 0:
                    start, end = cal[0], cal[-1]                     # full range
                else:
                    i = rng.randint(0, len(cal) - 300)
                    start, end = cal[i], cal[min(len(cal) - 1, i + rng.randint(60, 900))]
                txs = generate_transactions(seed=seed, start=start, end=end, max_per_day=1)
                for t in txs[::17]:
                    t["description"] = "ONLINE PAYMENT THANK YOU"    # non-purchases mixed in (R-1.4)
                for t in txs[::23]:
                    t["direction"] = "credit"                        # refunds (R-1.8)
                yield {"id": f"GEN-{family}-{style}-{seed}", "market": m, "transactions": txs,
                       "config": {"strategy": rng.choice(["threshold", "next_session", "weekly", "monthly"]),
                                  "start": start, "end": end,
                                  "reinvest": "true" if rng.randint(0, 3) else "false"}}


def main(n_seeds: int) -> int:
    total = bad = buys = 0
    t0 = time.time()
    for s in scenarios(n_seeds):
        mine, theirs = run_scenario(s), crosscheck.run(s)
        mine.pop("engine_version", None)
        d = diff(mine, theirs)
        total += 1
        buys += len(mine["buys"] or [])
        if d:
            bad += 1
            print(f"## {s['id']}: {d[:5]}")
    print(f"{total} generated scenarios, {buys} buys compared, {bad} with differences "
          f"({time.time() - t0:.0f}s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 26))
