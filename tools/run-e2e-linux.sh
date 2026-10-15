#!/bin/bash
# Runs the web end-to-end tests under LINUX fonts and rendering, in Playwright's official Ubuntu 24.04 image (the runner's OS) with
# the pinned Chromium. Text measured 279 px wide on macOS and 284 px under Linux, so layout checks must not be trusted from macOS alone
# (TEST-STRATEGY.md 0.1d).
#
#   tools/run-e2e-linux.sh                          # the whole suite, from the last commit (HEAD)
#   tools/run-e2e-linux.sh e2e/layout.spec.ts       # only some tests (arguments go to `playwright test`)
#
# Needs a container runtime that can mount your home directory (for example: brew install colima docker; colima start).
# The checkout is exported from git HEAD into ~/.cache/roundup-linux-run, so commit before running. Results: layout-linux.log there.
set -eu
IMAGE="mcr.microsoft.com/playwright:v1.64.0-noble"          # keep in step with @playwright/test in web/package.json
DIR="$HOME/.cache/roundup-linux-run"
rm -rf "$DIR"; mkdir -p "$DIR"
git -C "$(dirname "$0")/.." archive HEAD | tar -x -C "$DIR"
cat > "$DIR/inside.sh" <<'INSIDE'
set -u
cd /work
apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq python3-venv python3-pip >/dev/null 2>&1
python3 -m venv .venv && .venv/bin/pip install -q -r requirements-ci.txt -r requirements-test.txt
cd web && npm ci --no-audit --no-fund >/dev/null 2>&1
rm -rf .next
CI=1 npx playwright test "$@" --reporter=list > /work/layout-linux.log 2>&1
echo "playwright exit: $?"; grep -aE "passed|failed|skipped" /work/layout-linux.log
INSIDE
docker run --rm -v "$DIR":/work -w /work "$IMAGE" bash /work/inside.sh "$@"
echo "log: $DIR/layout-linux.log"
