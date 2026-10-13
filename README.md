# RoundUp

An educational, invite-only demo that simulates "spare-change" round-up investing on **synthetic** market scenarios. No money moves, nothing is a forecast, nothing is advice. Start with [PLAN.md](PLAN.md).

| Folder | What |
|---|---|
| `engine/` | `roundup_engine` (the simulation, Decimal-only) and `roundup_scenarios` (seeded synthetic markets) |
| `crosscheck/` | Independent second implementation (exact fractions) used to check the engine |
| `api/` | `roundup_api`, the FastAPI service ([API.md](API.md)) |
| `supabase/` | Database schema and row-level-security SQL, with its own README |
| `web/mocks/` | Static design mocks for review (not the real site) |

## Set up and run all tests (fresh environment)

From the repository root, with Python 3.12 or newer:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-test.txt

.venv/bin/python -m pytest -q engine                       # engine + scenario generator + cross-check agreement
.venv/bin/python -m pytest -q api/tests -W ignore::DeprecationWarning               # API tests
.venv/bin/python -m pytest -q api/tests_independent -W ignore::DeprecationWarning \
    -o pythonpath=api/tests_independent --rootdir=api/tests_independent              # independent API tests
```

Run the API locally: `.venv/bin/python -m uvicorn app:app` (uvicorn is not pinned; install it for local runs only).

## Deploying the API to Vercel

- The API is a Vercel project whose **Root Directory is the repository root**. Vercel resolves `app.py` → `roundup_api.main:app` and installs `requirements.txt`, which installs the two local packages `./engine` and `./api`.
- A project rooted at `api/` would not work: "Your app will not be able to access files outside of that directory. You also cannot use `..`" ([Vercel: Root Directory](https://vercel.com/docs/builds/configure-a-build#root-directory)).
- `vercel.json` excludes tests, mocks and docs from the function bundle.
- **Not yet verified on Vercel:** whether its Python installer accepts the local-path lines `./engine` and `./api`. Confirm on the first deploy.
- The web app will be a separate Vercel project rooted at `web/`.

**Troubleshooting (macOS, Python 3.13):** if an *editable* install (`pip install -e`) later fails with "No module named roundup_api", macOS may have marked the `.pth` files as hidden. Python 3.13 skips hidden `.pth` files (`python -v` prints "Skipping hidden .pth file"). On this machine the flag came back within minutes, so `chflags nohidden` is not a lasting fix. Use the non-editable install above (re-run it after code changes), or run scripts with `PYTHONPATH=engine/src:api`. The test suites already put the working tree on their path.
