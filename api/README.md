# roundup_api

FastAPI service for RoundUp ([API.md](../API.md)). It validates input, calls the engine, and never calculates.

```bash
python3 -m venv .venv && .venv/bin/pip install fastapi httpx "pyjwt[crypto]" pytest
.venv/bin/pytest -q -W ignore                       # main tests (contract, abuse, auth, logging, no-calculation)
.venv/bin/python -m pytest -q -W ignore tests_independent \
    -o pythonpath=". ../engine/src tests_independent" --rootdir=tests_independent   # independent tester's suite
```

`tests_independent/` was written by a separate agent that saw only API.md and the plan files, never this
code. Edits made afterwards are marked `EDITED` and explained in place. Each one followed a contract
correction, never an attempt to make a failure go away.

Local run: `SUPABASE_URL=... SUPABASE_PUBLISHABLE_KEY=... .venv/bin/uvicorn roundup_api.main:app`. Without
those variables everything works except saving.
