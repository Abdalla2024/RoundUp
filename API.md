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
| 422 | `WINDOW_OUTSIDE_DATA` | Dates outside the scenario's range, or start after end |
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
- Give either `transactions` (1–20,000 items) **or** `"generate": {"seed": 0..2147483647, "max_per_day": 1..3}`. Exactly one is required; both or neither → 422 `INVALID_INPUT`.
- Generated transactions are seeded synthetic purchases (R-1.7) between `start` and `end`.

**Meta** (in every simulation-type response):
```json
{"engine_version": "0.2.0", "model_version": "scenario-model-1", "scenario_id": "steady-growth",
 "style": "broad", "scenario_seed": 1101, "market_checksum": "<sha256 hex>",
 "input_checksum": "<sha256 hex>", "label": "Synthetic scenario. Not a real fund, not real prices, and not a forecast."}
```
- `market_checksum` is the engine's checksum of the market series.
- `input_checksum` is the engine's SHA-256 of the canonical scenario input (market checksum + transactions + config). The same request always gives the same `input_checksum`.

**Result:** exactly the engine result format in `engine/fixtures/FORMAT.md` (`status`, `summary`, `buys`, `series`, …), unchanged, plus `engine_version`.

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
- `difference` is computed by the engine (`roundup_engine.compare`) as b − a for: `ending_value`, `gain`, `dividends_earned`, `uninvested_cash`, `roundup_buys`, `dividend_buys`. Money is shown to the cent.
- If either run fails with a data error, the response is 422 with that error code.

### `POST /v1/transactions/parse`
Body:
```json
{"csv": "<text>", "mapping": {"date": "Date", "posted_date": null, "amount": "Amount", "debit": null,
 "credit": null, "type": null, "status": null, "description": "Description", "external_id": null,
 "account": null}, "sign_convention": null}
```
- `sign_convention` is optional: `separate_columns`, `type_column`, `debits_positive` or `debits_negative`.
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
- It computes the result with the engine, then inserts `app.scenarios` and `app.scenario_results` through the Supabase Data API, **forwarding the user's token** so RLS applies.
- Transactions are saved only if `save_transactions` is true, and never with descriptions.

Signed-out users can use every endpoint except this one.

## Configuration and testing hooks

Production configuration comes from environment variables: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `LOG_SALT`. Without `SUPABASE_URL`, `POST /v1/saved` returns 503 `STORAGE_UNAVAILABLE`; everything else works.

Tests build an app with the factory:

```python
from roundup_api.main import create_app
app = create_app(
    supabase_url="https://example-ref.supabase.co",  # issuer is "<supabase_url>/auth/v1"
    publishable_key="test-publishable-key",
    jwks={"keys": [...]},              # use this JWKS instead of fetching <supabase_url>/auth/v1/.well-known/jwks.json
    storage_transport=httpx.MockTransport(handler),  # receives the Data API calls (POST <supabase_url>/rest/v1/<table>)
    rate_limits=None,                  # optional dict overriding per-route limits, e.g. {"simulate": 3}
)
```

- `roundup_api.main:app` is the default app built from the environment.
- Storage calls are `POST <supabase_url>/rest/v1/scenarios`, then `POST <supabase_url>/rest/v1/scenario_results`. Each carries the headers `apikey: <publishable_key>`, `Authorization: Bearer <the user's token>`, `Prefer: return=representation` and `Content-Type: application/json`. A successful insert answers `201` with a JSON array of the created rows ([PostgREST](https://github.com/PostgREST/postgrest/blob/main/docs/references/api/preferences.rst)). The `scenarios` row's `id` is the `id` returned by `POST /v1/saved`.
- `rate_limits` keys: `simulate`, `compare`, `parse`, `saved`, `read`.
