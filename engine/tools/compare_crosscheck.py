"""Compare engine output with the independent implementation's results.json, field by field.

    python tools/compare_crosscheck.py path/to/results.json
"""

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(HERE / "src")]

from roundup_engine import run_scenario  # noqa: E402

IGNORED_KEYS = {"engine_version"}


def diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted((set(a) | set(b)) - IGNORED_KEYS):
            out += diff(a.get(k, "<missing>"), b.get(k, "<missing>"), f"{path}.{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        out = [] if len(a) == len(b) else [(f"{path}.len", len(a), len(b))]
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [(path, a, b)]


def main(results_path: str) -> int:
    other = json.loads(pathlib.Path(results_path).read_text())
    total = mismatched = 0
    for f in sorted((HERE / "fixtures" / "scenarios").glob("*.json")):
        s = json.loads(f.read_text())
        mine = run_scenario(s)
        theirs = other.get(s["id"])
        total += 1
        d = diff(mine, theirs) if theirs is not None else [("<scenario>", "present", "missing")]
        if d:
            mismatched += 1
            print(f"## {s['id']}: {len(d)} difference(s)")
            for p, a, b in d[:15]:
                print(f"   {p}: engine={a!r} crosscheck={b!r}")
    print(f"\n{total} scenarios, {total - mismatched} identical, {mismatched} with differences")
    return 1 if mismatched else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
