"""The API for local end-to-end tests ONLY (web/playwright.config.ts): the same app, with the per-minute rate limits raised so
that several browser suites sharing one local address do not trip them (parse is limited to 10 a minute by default).
The deployed API never uses this file; its limits are the defaults in api/roundup_api/ratelimit.py."""

import os

from roundup_api.main import create_app

HIGH = 1_000_000
app = create_app(supabase_url=os.environ.get("SUPABASE_URL"), publishable_key=os.environ.get("SUPABASE_PUBLISHABLE_KEY"),
                 allowed_origin=os.environ.get("ALLOWED_ORIGIN"),
                 rate_limits={"simulate": HIGH, "compare": HIGH, "parse": HIGH, "saved": HIGH, "read": HIGH})
