# roundup_api

FastAPI service for RoundUp ([API.md](../API.md)). It validates input, calls the engine, and never calculates.

Setup and test commands: see the root [README.md](../README.md#set-up-and-run-all-tests-fresh-environment).

`tests_independent/` was written by a separate agent that saw only API.md and the plan files, never this
code. Edits made afterwards are marked `EDITED` and explained in place. Each one followed a contract
correction, never an attempt to make a failure go away.

Local run, from the repo root: `SUPABASE_URL=... SUPABASE_PUBLISHABLE_KEY=... .venv/bin/python -m uvicorn app:app`. Without
those variables everything works except saving.
