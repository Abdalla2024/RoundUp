# RoundUp API contract (v1)

FastAPI service. Package `roundup_api` (in `api/`); the app object is `roundup_api.main:app`. All paths are under `/v1`. Requests and responses are JSON (`Content-Type: application/json`), except where stated. **The API never calculates.** Every financial number comes from the engine (`roundup_engine`), and the scenario series come from `roundup_scenarios` (SCENARIO-MODEL.md).

## Conventions

- **Unknown fields are rejected** (422 `UNKNOWN_FIELD`) at every level of every request body.
- **Strict types:** no coercion.
  - Booleans must be JSON `true`/`false`.
  - Money amounts must be **strings** like `"4.37"`; JSON numbers are rejected.
  - Integers must be JSON integers.
  - Dates are `"YYYY-MM-DD"` strings.
- **Size limits:**
  - Any request body is at most **3,000,000 bytes**; larger → 413 `PAYLOAD_TOO_LARGE`, checked before parsing.
  - `transactions` arrays hold at most **20,000** items.
  - `csv` text is at most **2,000,000** characters and **20,000** data rows.
  - Strings: `description` ≤ 140 characters, `name` ≤ 80, CSV column names ≤ 100.
- **Errors** always look like this, with a plain-language `message` that never contains stack traces or internal details:
  ```json
  {"error": {"code": "SOME_CODE", "message": "Plain-language sentence.", "fields": ["transactions.3.amount"]}}
  ```
  `fields` is present only for validation errors. It lists the paths of the offending fields.
- **Every response** has an `X-Request-ID` header. A client-supplied `X-Request-ID` is ignored and a fresh one is generated.

| HTTP | `code` | When |
|---|---|---|
| 400 | `INVALID_JSON` | Body is not valid JSON, or the top level is not an object |
| 401 | `AUTH_REQUIRED` | Save endpoint with no `Authorization: Bearer` token |
| 401 | `AUTH_INVALID` | Token malformed, bad signature, wrong algorithm, expired, wrong audience or issuer, missing claims, or anonymous user |
| 404 | `NOT_FOUND` | Unknown path |
| 404 | `UNKNOWN_SCENARIO` | `scenario_id` / `style` not in `GET /v1/scenarios` |
| 405 | `METHOD_NOT_ALLOWED` | Wrong method |
| 413 | `PAYLOAD_TOO_LARGE` | Body over the limit |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | POST without `Content-Type: application/json` |
| 422 | `UNKNOWN_FIELD` | Unexpected field anywhere |
| 422 | `INVALID_INPUT` | Wrong type, bad format, out of range, too many items |
| 422 | `WINDOW_OUTSIDE_DATA` | Dates outside the scenario's range, start after end, or no trading day between the dates (stage 5: a weekend- or holiday-only window used to return an empty series) |
| 422 | `SIGN_CONVENTION_REQUIRED` | CSV sign convention cannot be inferred and was not given (R-1.3) |
| 422 | `CSV_INVALID` | CSV cannot be parsed (binary data, NUL bytes, bad quoting, mapped column missing, too many rows) |
| 429 | `RATE_LIMITED` | Too many requests; a `Retry-After` header gives seconds |
| 500 | `INTERNAL` | Unexpected failure (generic message) |
| 503 | `STORAGE_UNAVAILABLE` | Saving is not configured or the database did not respond |

**Rate limits** (per client IP, per minute):
- `POST /v1/simulate` and `POST /v1/compare`: 30.
- `POST /v1/transactions/parse`: 10.
- `POST /v1/saved`: 10.
- `GET` endpoints: 120.

The limits are kept in memory per server instance (see OPERATIONS.md).

## Shared objects

**Transaction** (input):
```json
{"posted_date": "2024-01-03", "amount": "4.37", "direction": "debit",
 "status": "posted", "category": "purchase", "description": "COFFEE"}
```
- `posted_date`, `amount` and `direction` are required.
- `direction` is one of `debit`, `credit`.
- `status` is optional: `posted` (default), `pending` or `cancelled`.
- `category` is optional: `purchase` or `non_purchase`. It overrides keyword classification, so the user can reclassify a row (R-1.4).
- `description` is optional, ≤ 140 characters, and used only for classification (R-1.4). It is **never stored, logged or echoed**.
- `amount` must match `^\d{1,7}(\.\d{1,2})?$`. Amounts with 3 decimals, signs, or other text are rejected with 422 `INVALID_INPUT`. This is stricter than the engine, which ignores such rows; the API refuses them outright.

**Run options:**
```json
{"scenario_id": "steady-growth", "style": "broad", "start": "2015-01-02", "end": "2020-12-31",
 "transactions": [ ... ]}
```
- Optional `"buys": "all"` (default) or `"none"`. With `"none"` the engine leaves out the per-buy list: `buys` is `[]` and `"buys_included": false`. The summary counts are unchanged. Over a full 2012–2026 range the buy list is most of the response, and the screens show only counts.
- Give either `transactions` (1–20,000 items) **or** `"generate": {"seed": 0..2147483647, "max_per_day": 1..3}`. Exactly one is required; both or neither → 422 `INVALID_INPUT`.
- Generated transactions are seeded synthetic purchases (R-1.7) between `start` and `end`.

**Meta** (in every simulation-type response):
```json
{"engine_version": "0.2.0", "model_version": "scenario-model-1", "scenario_id": "steady-growth",
 "style": "broad", "scenario_seed": 1101, "market_checksum": "<sha256 hex>",
 "input_checksum": "<sha256 hex>", "label": "Synthetic scenario. Not a real fund, not real prices, and not a forecast."}
```
- `market_checksum` is the engine's checksum of the market series.
- `input_checksum` is the engine's SHA-256 of the canonical scenario input: the market checksum, plus each transaction's date, amount, direction, status and **resolved category**, plus the config. Descriptions never feed the checksum (D-8). The same request always gives the same `input_checksum`. For compare, it covers the shared input with the default config, before the a/b overrides.

**Result:** exactly the engine result format in `engine/fixtures/FORMAT.md` (`status`, `summary`, `buys`, `series`, …), unchanged, plus `engine_version`. The API asks the engine for `auto` chart points. Ranges up to 366 days get daily points; longer ranges get one point per week (the week's last trading day, plus the final day). The engine adds `series_resolution` and `series_rule`, and the chart must show `series_rule` (owner decision). All totals are computed daily either way.

The summary also carries the stage-5 engine figures (FORMAT.md):
- `roundups_waiting` + `dividends_as_cash` = `uninvested_cash`;
- `deepest_dip`: the day the value was furthest below the round-ups added, or `null`.

The browser shows these strings as they are and never derives them.

## Endpoints

### `GET /v1/health`
200:
```json
{"status": "ok", "engine_version": "...", "model_version": "...", "scenarios": 4}
```
It runs a tiny engine self-check. If that fails: 503 with `{"status": "degraded", ...}`.

### `GET /v1/scenarios`
200:
```json
{"label": "...", "model_version": "...", "scenarios": [{"id": "steady-growth", "name": "Steady growth",
 "description": "...", "label": "...", "seed": 1101, "styles": [{"style": "broad",
 "name": "Broad-market style (synthetic)", "symbol": "SYN-STEADY-GROWTH-BROAD", "start": "2012-01-03",
 "end": "2026-09-30", "market_checksum": "...", "parameters": {...}}]}]}
```
There are 4 scenarios, each with 2 styles (`broad`, `dividend`).

### `GET /v1/assumptions`
200:
```json
{"disclaimer": "...", "assumptions": [{"id": "R-2.2", "title": "...", "text": "..."}]}
```
Plain-language statements of the main rules. Each `id` is a FINANCE-RULES rule ID. The list includes at least R-2.1/2.2, R-5.1/5.2, R-7.1, R-8.5, R-10.1, R-10.4, R-11.3 and R-12.5, and the sample-data label.

### `POST /v1/simulate`
Body: run options, plus `"strategy"` (`threshold` | `next_session` | `weekly` | `monthly`) and `"reinvest"` (boolean).

200:
```json
{"result": <engine result>, "meta": <meta>}
```
The result equals what `roundup_engine.run_scenario` returns for the same scenario.

### `POST /v1/compare`
Body: run options, plus `"a": {"strategy": ..., "reinvest": ...}` and `"b": {...}`.

200:
```json
{"a": <engine result>, "b": <engine result>, "difference": {...}, "meta": <meta>}
```
- `difference` is computed by the engine (`roundup_engine.compare`) as b − a for: `ending_value`, `gain`, `dividends_earned`, `uninvested_cash`, `roundup_buys`, `dividend_buys`. Like every engine result value, each is a **string**: money to the cent with a leading `-` when negative (e.g. `"-12.34"`, `"0.00"`), and counts as integer strings (e.g. `"-1"`, `"0"`).
- If either run fails with a data error, the response is 422 with that error code.

### `POST /v1/transactions/parse`
Body:
```json
{"csv": "<text>", "mapping": {"date": "Date", "posted_date": null, "amount": "Amount", "debit": null,
 "credit": null, "type": null, "status": null, "description": "Description", "external_id": null,
 "account": null}, "sign_convention": "debits_positive"}
```
- `sign_convention` is optional: `separate_columns`, `type_column`, `debits_positive` or `debits_negative`. If it is null, it is inferred **only** from the column layout: separate debit/credit columns give `separate_columns`, and a type column whose values are all debit/credit gives `type_column`. A single signed amount column is never guessed from its values; it returns 422 `SIGN_CONVENTION_REQUIRED` (R-1.3, no silent default). An explicit convention must fit the mapping, otherwise the response is 422 `INVALID_INPUT` with `fields: ["sign_convention", "mapping.<missing>"…]` and a message naming the missing column, e.g. "Choose which column holds the amount." (stage 5). Amounts over the `/v1/simulate` limit (more than 7 digits before the point) are reported as `invalid_amount`, so every usable row is accepted by `/v1/simulate` (stage 5). `separate_columns` needs `debit` and `credit`; `type_column` needs `type` and `amount`; `debits_positive` and `debits_negative` need `amount`.
- `mapping` values are column names, or null.

200:
```json
{"columns": ["Date", "Amount", "Description"], "date_column_used": "Date",
 "sign_convention": "debits_positive",
 "transactions": [{"row": 2, "posted_date": "2024-01-03", "amount": "4.37", "direction": "debit",
   "status": "posted", "category": "purchase", "problem": null}],
 "summary": {"rows": 1, "usable": 1, "problems": {"invalid_amount": 0, "invalid_date": 0, "zero_amount": 0},
   "non_purchases": 0, "possible_duplicates": 0}}
```
- `row` is the line number in the file (header = 1).
- **Descriptions are never returned.** Classification happens here and is returned as `category`.
- **Error messages never echo user-supplied text.** A missing mapped column is reported through `fields` (e.g. `["mapping.date"]`).
- **Echoed text** (column names) is neutralised against spreadsheet formula injection: any value starting with `=`, `+`, `-`, `@`, tab, CR, LF, or a full-width `＝＋－＠` gets a leading `'`.
- Nothing is stored.

### `POST /v1/saved` (signed-in users only)
Header `Authorization: Bearer <Supabase access token>`.

Body: the simulate body, plus `"name"` (1–80 characters) and `"save_transactions"` (boolean).

201:
```json
{"id": "<uuid>", "result": <engine result>, "meta": <meta>}
```
- The API verifies the token (Supabase JWKS; ES256/RS256 only; `aud` = `authenticated`; `iss` = `<SUPABASE_URL>/auth/v1`; `exp`, `sub`, `iss` and `aud` required; `sub` a UUID; `is_anonymous` not true).
- It computes the result with the engine, then makes **one** call, `POST <SUPABASE_URL>/rest/v1/rpc/save_scenario`, through the Supabase Data API, **forwarding the user's token** so RLS applies. The function (`supabase/migrations/0002_rls.sql`) inserts the scenario and its result in one transaction, with the owner taken from `auth.uid()`. PostgREST returns the scalar result, the new id, as a bare JSON value with HTTP 200 ([PostgREST functions](https://github.com/PostgREST/postgrest/blob/main/docs/references/api/functions.rst)). Any other answer gives 503 `STORAGE_UNAVAILABLE`. This closes question #34 below (no partial saves).
- Transactions are saved only if `save_transactions` is true, and never with descriptions.

Signed-out users can use every endpoint except this one.

## Configuration and testing hooks

Production configuration comes from environment variables: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `LOG_SALT`, `ALLOWED_ORIGIN`, and `ROUNDUP_TRUST_PROXY=1` on Vercel. That last one makes the client IP come from `X-Forwarded-For`, which Vercel overwrites to prevent spoofing ([Vercel request headers](https://vercel.com/docs/headers/request-headers)). Without it, the socket address is used.

**CORS:** `ALLOWED_ORIGIN` is the web project's default Vercel address, e.g. `https://<web-project>.vercel.app` (owner decision). It is the **only** origin allowed, with methods `GET` and `POST`, headers `Content-Type` and `Authorization`, and exposed headers `X-Request-ID` and `Retry-After`. Credentials (cookies) are not allowed: the token travels in the `Authorization` header. Without `ALLOWED_ORIGIN`, no CORS headers are sent, so browsers on other sites cannot read responses ([FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)). Without `SUPABASE_URL`, `POST /v1/saved` returns 503 `STORAGE_UNAVAILABLE`; everything else works.

Tests build an app with the factory:

```python
from roundup_api.main import create_app
app = create_app(
    supabase_url="https://example-ref.supabase.co",  # issuer is "<supabase_url>/auth/v1"
    publishable_key="test-publishable-key",
    jwks={"keys": [...]},              # use this JWKS instead of fetching <supabase_url>/auth/v1/.well-known/jwks.json
    storage_transport=httpx.MockTransport(handler),  # receives the Data API calls (POST <supabase_url>/rest/v1/<table>)
    rate_limits=None,                  # optional dict overriding per-route limits, e.g. {"simulate": 3}
    slow_ms=2000,                      # requests at or above this latency are logged with "slow": true
)
```

- `roundup_api.main:app` is the default app built from the environment.
- The storage call is `POST <supabase_url>/rest/v1/rpc/save_scenario`, with the headers `apikey: <publishable_key>`, `Authorization: Bearer <the user's token>` and `Content-Type: application/json`. The body holds the function's `p_*` parameters. Success is `200` with the new id as a bare JSON string, which is the `id` returned by `POST /v1/saved`.
- `allowed_origin=` (optional) turns on CORS for that single origin.
- `rate_limits` keys: `simulate`, `compare`, `parse`, `saved`, `read`.

## Resolved questions (from the independent contract review)

An independent tester, working only from this contract, listed 42 ambiguities (`api/tests_independent/ATTACKS.md`). The current behaviour, now normative:

| # | Question | Answer |
|---|---|---|
| 1, 40 | Body size | The real byte count is authoritative. A declared `Content-Length` over the limit is refused early with 413. Exactly 3,000,000 bytes is accepted. |
| 2 | Order of checks | **POST:** rate limit (429) → content type (415) → size (413) → JSON (400) → schema (422; `UNKNOWN_FIELD` wins over `INVALID_INPUT`) → engine (422). **`/v1/saved`:** storage configured (503) → token (401) → then the same order. |
| 3, 4, 6 | Duplicate keys, `NaN`/`Infinity`, invalid UTF-8 in the JSON body | 400 `INVALID_JSON`. A leading UTF-8 BOM is tolerated (skipped). |
| 5 | Content-Type | Case-insensitive; parameters such as `; charset=utf-8` are allowed. |
| 7 | Explicit `null` | Allowed for `category` and `description`; refused (422) for `status`, which must be omitted to get the default. |
| 8, 9, 10 | Dates | `start` and `end` are required. `start == end` is allowed, and so are non-trading days at either end, but the window must contain at least one trading day (otherwise 422 `WINDOW_OUTSIDE_DATA`, stage 5). Transactions outside the window are ignored by the engine (R-1.6) and counted in `transactions_ignored`. |
| 11, 26 | `input_checksum` | Described under Meta above. |
| 12 | Length limits | Counted in Unicode code points. The body limit is in bytes. |
| 13, 14 | CSV limits | An over-long `csv` gives 422 `INVALID_INPUT`. Any header name over 100 characters, or more than 50 columns, gives 422 `CSV_INVALID`. |
| 15 | `columns` | Echoes every header name, neutralised. Cell values from unmapped columns are never returned. |
| 16 | `mapping` | Keys may be omitted (= null). If both `date` and `posted_date` are mapped, `posted_date` wins (R-1.2). |
| 17 | Sign convention | Described under the parse endpoint. |
| 18 | `row` | The CSV record number, with the header as row 1. A quoted multi-line field counts as one record. Blank lines are skipped but keep their numbers. |
| 19 | Problem rows | Included, with `problem` set to `invalid_amount`, `invalid_date` or `zero_amount`. `amount` is null for invalid amounts. A leading `+` is invalid. |
| 20 | Malformed CSV | Ragged rows: missing cells are empty and extra cells are ignored. Stray quotes, NUL or binary data, and an empty file give 422 `CSV_INVALID`. A header-only file returns zero transactions. A UTF-8 BOM is stripped. |
| 21 | Echo in errors | Never: see the parse endpoint. |
| 22 | Parse → simulate | The client must drop `row` and `problem` (and rows with problems) before sending transactions to `/simulate`, which rejects unknown fields. |
| 23, 24 | `fields` | Present for `INVALID_INPUT`, `UNKNOWN_FIELD` and mapping-related `CSV_INVALID`. Each entry is a dotted path to the offending key, e.g. `transactions.0.memo`. |
| 25 | Ill-formed `scenario_id` | Up to 64 characters: 404 `UNKNOWN_SCENARIO`. Longer: 422 `INVALID_INPUT`. |
| 27 | `difference` format | Strings: see compare above. |
| 28 | Result format | `engine/fixtures/FORMAT.md`. |
| 29 | Authorization header | A missing or empty token, or a scheme other than exactly `Bearer `, gives 401 `AUTH_REQUIRED`. |
| 30 | Token claims | Algorithm ES256/RS256 only. A `kid` present in the JWKS is required. `aud` may be a string or a list containing `authenticated`. `exp` is required, and `exp`/`iat`/`nbf` must be integers when present. 10 s leeway. `is_anonymous`, if present, must be exactly `false`. |
| 31 | Tokens on open endpoints | Ignored. |
| 32 | No `SUPABASE_URL` | 503 before any token check. |
| 33 | Data API answers anything but 201 | 503 `STORAGE_UNAVAILABLE`. |
| 34 | Partial save | **Resolved (stage 5):** one call to the atomic `save_scenario()` function. Either both rows are stored or neither (verified on local Postgres, `supabase/tests`). |
| 35 | Stored row shapes | Sent to the `public` schema (no `Content-Profile`). `user_id` is sent explicitly and RLS `with check` verifies it equals `auth.uid()`. Saved transactions use the API's decimal-string format, without descriptions. Deleted users: the token stays valid until `exp`, but the insert then fails its foreign key, giving 503. |
| 36 | Rate limits | Separate buckets per route group. Sliding 60 s window. Every request counts, including 4xx; `/v1/health` counts toward `read`. `Retry-After` is 1–60. Client IP rules: Configuration section. Per-user limits are not implemented (explainer stage). State is per app instance. |
| 37 | Other paths | `/docs`, `/redoc` and `/openapi.json` are disabled (404). Unknown query parameters are ignored. CORS: see Configuration (one allowed origin). |
| 38 | Degraded health | Returns 503 with the health body, not the error envelope. This is deliberate, so monitors can read the fields. |
| 39 | Label | `meta.label` is exactly the `LABEL` constant in `roundup_scenarios`. |
| 41 | `generate` + `save_transactions` | The generated transactions are saved. |
| 42 | Sample-data label in assumptions | It is the R-12.5 entry. |
