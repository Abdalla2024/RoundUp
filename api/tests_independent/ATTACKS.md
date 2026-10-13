# RoundUp API v1: attack catalogue

Written only from `API.md` (plus PLAN.md, SECURITY-PRIVACY.md and OPERATIONS.md as context). The implementation was not seen. Every attack also checks that the response has `X-Request-ID`, uses the `{"error": {...}}` envelope, and contains no stack trace, file path or framework detail (`apisupport.LEAK_MARKERS`). A 500 is always a failure.

Files: `apisupport.py` (helpers, fake Data API, key/JWKS/token builders), `conftest.py` (fixtures), `test_contract.py`, `test_attacks.py`. Run with `pytest` from this folder once `roundup_api` is importable.

## Attacks and expected responses

| # | Attack | Expected per contract | Test(s) |
|---|---|---|---|
| 1 | Body of exactly 3,000,000 bytes (valid JSON padded with whitespace) | 200 | `test_body_exactly_at_limit_is_accepted` |
| 2 | Body of 3,000,001 bytes, truthful Content-Length | 413 `PAYLOAD_TOO_LARGE` | `test_body_one_byte_over_limit_is_413` |
| 3 | Oversize body that is also invalid JSON | 413, not 400 ("checked before parsing") | `test_oversize_invalid_json_is_413_not_400` |
| 4 | Oversize body sent chunked, no Content-Length | 413 | `test_oversize_without_content_length_chunked` |
| 5 | Oversize body with a lying small Content-Length | 413 or 400 (ambiguous) | `test_oversize_with_lying_small_content_length` |
| 6 | Tiny body with a huge declared Content-Length | 413 (or 400/422; ambiguous) | `test_oversize_with_huge_declared_content_length` |
| 7 | Over 3 MB built from 19,000 transactions × 140-char descriptions | 413 | `test_oversize_via_many_long_descriptions` |
| 8 | 20,001 transactions (body under 3 MB) | 422 `INVALID_INPUT`, `fields` contains `transactions` | `test_too_many_transactions`, `..._compare` |
| 9 | Non-object top level (`[]`, `"s"`, `1`, `null`, `true`), empty body, trailing comma, single quotes, two concatenated objects, NUL | 400 `INVALID_JSON` | `test_not_a_json_object` |
| 10 | Invalid UTF-8 bytes in the body | 400 `INVALID_JSON` (422 also accepted) | `test_invalid_utf8_body` |
| 11 | Deeply nested arrays/objects (1,000 and 100,000 levels) | 400 or 422, never 500 (RecursionError) | `test_deeply_nested_*` |
| 12 | Unknown field at top level, in a transaction, in `generate`, in compare `a`, in `mapping`, in the parse body, in the saved body | 422 `UNKNOWN_FIELD` with the field path | `test_unknown_fields_rejected_at_every_level` |
| 13 | Unknown fields named like internals (`config`, `fee`, `__proto__`, …) | 422 `UNKNOWN_FIELD` | `test_unknown_field_with_engine_looking_names` |
| 14 | `amount` as a JSON number (`4.37`, `4`, `0`, `1e2`, `-4.37`) | 422 `INVALID_INPUT`, `transactions.0.amount` | `test_amount_as_json_number_rejected` |
| 15 | Bad amount strings: 3 decimals, signs, spaces, trailing `\n`, comma, `1e3`, 8 digits, hex, NaN, full-width `４.３７`, Arabic-Indic `٤.٣٧`, zero-width space, `1_000`, SQL text | 422 `INVALID_INPUT` (note that Python `\d` and `$` accept Unicode digits and a trailing newline) | `test_bad_amount_strings` |
| 16 | Booleans as strings or ints (`"true"`, `1`, `null`) | 422 `INVALID_INPUT` | `test_reinvest_must_be_boolean`, `test_saved_strict_types` |
| 17 | Integers as strings/floats/booleans (`"5"`, `5.0`, `true`) | 422 `INVALID_INPUT` | `test_seed_must_be_integer`, `test_max_per_day_must_be_integer` |
| 18 | 5,000-digit integer seed (Python's int-string limit) | 400 or 422, never 500 | `test_huge_integer_seed` |
| 19 | `NaN` / `Infinity` / `-Infinity` tokens (Python's `json` accepts them by default) | 400 `INVALID_JSON` or 422 `INVALID_INPUT` | `test_nan_infinity_tokens` |
| 20 | Duplicate keys (`"reinvest": true, "reinvest": "x"`) | Not specified; must not be 500 and must not accept a non-boolean | `test_duplicate_keys` |
| 21 | Bad dates (`2024-1-3`, `2023-02-29`, `20240103`, datetime, `DD/MM/YYYY`, number, full-width digits) | 422 `INVALID_INPUT` | `test_bad_transaction_field_types` |
| 22 | Missing / wrong Content-Type (`text/plain`, form, multipart, `application/jsonx`, …) | 415 `UNSUPPORTED_MEDIA_TYPE` | `test_wrong_content_type`, `test_multipart_csv_upload_refused` |
| 23 | `application/json; charset=utf-8`, `Application/JSON` | 200 expected; 415 accepted (ambiguous) | `test_json_content_type_variants` |
| 24 | CSV with NUL bytes (in a cell, in a header) | 422 `CSV_INVALID` | `test_csv_with_nul_bytes`, `test_csv_nul_in_header` |
| 25 | Binary CSV (control bytes; ZIP/XLSX magic) | 422 `CSV_INVALID` | `test_csv_binary_data`, `test_csv_looks_like_zip_or_xlsx` |
| 26 | Unterminated quote | 422 `CSV_INVALID` | `test_csv_unterminated_quote` |
| 27 | Stray quote inside an unquoted field; ragged rows; empty or header-only CSV | 200 or 422, never 500 (ambiguous) | `test_csv_stray_quote_*`, `test_csv_ragged_rows`, `test_csv_empty_or_header_only` |
| 28 | CSV with 20,001 data rows (and with blank lines interleaved) | 422 `CSV_INVALID` | `test_csv_20001_rows_rejected`, `test_csv_blank_lines_do_not_bypass_row_limit` |
| 29 | CSV with exactly 20,000 rows | 200 | `test_csv_20000_rows_accepted` |
| 30 | CSV over 2,000,000 characters | 422 (`INVALID_INPUT` or `CSV_INVALID`; ambiguous) | `test_csv_over_2m_characters` |
| 31 | 1.9 M three-byte characters (under the char limit, over the byte limit) | 413 | `test_csv_char_limit_counts_characters_not_bytes` |
| 32 | 1,000,000-character cell | Never echoed; small response | `test_csv_extremely_long_cell_not_echoed` |
| 33 | CSV header over 100 characters, unmapped / mapped | Unmapped: 200 or 422 (ambiguous); mapped: 422 | `test_csv_column_name_over_100_chars`, `test_mapping_column_name_over_100_chars` |
| 34 | Formula-injection headers: `=cmd|' /C calc'!A0`, `+1`, `-1`, `@SUM`, tab/CR/LF prefixed, full-width `＝＋－＠`, `=HYPERLINK` | Every echoed column name and `date_column_used` gets a leading `'` | `test_parse_neutralises_*`, `test_formula_injection_header_echo_is_neutralised`, `test_formula_injection_in_mapped_date_column` |
| 35 | Formula-injection cells in description, amount and date columns | Description never echoed; no returned string starts with a formula character | `test_formula_injection_cells` |
| 36 | Mapping names a missing column that is itself a formula | 422 `CSV_INVALID`; the formula is not echoed | `test_formula_injection_in_missing_mapping_error_not_echoed` |
| 37 | Card / IBAN numbers in cells | Never echoed (SECURITY-PRIVACY §2) | `test_account_number_like_values_not_echoed` |
| 38 | Script / HTML / template / log4j / SQL strings in `description` | Never echoed by simulate, compare, parse, or any error | `test_description_payloads_never_echoed`, `test_description_not_echoed_*`, `test_huge_description_rejected_not_echoed` |
| 39 | Path traversal, NUL, case, whitespace, SQL, `__proto__` and 100 KB scenario ids; hostile styles | 404 `UNKNOWN_SCENARIO` (422 `INVALID_INPUT` accepted) | `test_hostile_scenario_ids`, `test_hostile_styles` |
| 40 | Encoded traversal in URL paths | 404, nothing from the filesystem | `test_hostile_paths` |
| 41 | SQL-looking saved `name`, CSV headers and cells | Treated as data; name goes in the JSON body, never the URL | `test_sql_injection_name_is_stored_as_plain_data`, `test_sql_looking_csv_and_mapping` |
| 42 | Unicode: RTL override, zero-width, emoji, combining marks, BOM, NUL, U+2028, lone surrogate | 200 or 422/400, never 500, never echoed | `test_unicode_*`, `test_lone_surrogate_in_description` |
| 43 | 140 vs 141 emoji in `description` | 141 → 422; 140 → 200 expected, 422 accepted (ambiguous) | `test_description_length_counts_code_points` |
| 44 | Rate-limit exhaustion for each route key (`simulate`, `compare`, `parse`, `read`, `saved`) through `rate_limits` | 429 `RATE_LIMITED`, `Retry-After` integer seconds 1–60; other routes unaffected; nothing written once limited | `test_rate_limit_*_override` |
| 45 | Default limits (parse 10, simulate 30) | 429 on the 11th / 31st request | `test_rate_limit_default_*` |
| 46 | Rotating `X-Request-ID` to dodge the limiter | Still 429 | `test_rate_limit_not_bypassed_by_request_id_or_invalid_bodies` |
| 47 | No `Authorization` header | 401 `AUTH_REQUIRED`, no storage call | `test_saved_requires_token`, `test_missing_or_non_bearer_auth` |
| 48 | `Bearer ` (empty), `Bearer`, `Basic …`, `Token …`, `JWT …` | 401 (`AUTH_REQUIRED` or `AUTH_INVALID`; ambiguous) | `test_missing_or_non_bearer_auth` |
| 49 | `alg: none` / `None` (with and without kid) | 401 `AUTH_INVALID` | `test_bad_tokens_rejected` |
| 50 | HS256 signed with the publishable key; HS256 signed with the RSA public PEM (key confusion); JWKS that contains an `oct` key | 401 `AUTH_INVALID` | `test_bad_tokens_rejected`, `test_jwks_with_only_hmac_key_does_not_enable_hs256` |
| 51 | RS384 / PS256 with a trusted key; header changed to ES384 | 401 `AUTH_INVALID` (ES256/RS256 only) | `test_bad_tokens_rejected` |
| 52 | Expired; missing `exp`; `exp` as string | 401 `AUTH_INVALID` | `test_bad_tokens_rejected` |
| 53 | Wrong `aud` (`anon`, `service_role`), missing `aud` | 401 `AUTH_INVALID` | `test_bad_tokens_rejected` |
| 54 | Wrong `iss` (other project, no `/auth/v1`, `http://`), missing `iss` | 401 `AUTH_INVALID` | `test_bad_tokens_rejected` |
| 55 | Missing `sub`; `sub` non-UUID / empty / SQL / UUID + suffix / number | 401 `AUTH_INVALID` | `test_bad_tokens_rejected` |
| 56 | `is_anonymous: true` | 401 `AUTH_INVALID` | `test_bad_tokens_rejected` |
| 57 | Signed by a key not in the JWKS (same kid, unknown kid; EC and RSA) | 401 `AUTH_INVALID` | `test_bad_tokens_rejected` |
| 58 | Tampered payload; truncated / empty signature; garbage; 2 or 4 segments; bad base64; non-object JSON | 401 `AUTH_INVALID` | `test_bad_tokens_rejected` |
| 59 | 60 KB token | 400/401/413/431, never 500 | `test_bad_tokens_rejected[huge_token]` |
| 60 | Valid token + invalid body | 422, nothing written | `test_invalid_body_with_valid_token_writes_nothing` |
| 61 | Data API down / timing out | 503 `STORAGE_UNAVAILABLE` | `test_saved_storage_not_responding`, `test_storage_failures_are_plain` |
| 62 | Data API 500 / 401 / 403 RLS / non-JSON / empty array / second insert fails | 5xx (or 401/403) in the error envelope; no database detail leaked | `test_storage_failures_are_plain` |
| 63 | `SUPABASE_URL` unset | `/v1/saved` 503 `STORAGE_UNAVAILABLE`; everything else works | `test_saved_storage_unavailable_without_supabase_url` |
| 64 | Client-supplied `X-Request-ID` (including script and 5 KB values) | Ignored; a fresh id is generated | `test_every_response_has_fresh_request_id`, `test_client_request_id_injection_ignored` |
| 65 | Many malformed bodies | 4xx in the error envelope, plain message, no internals | `test_errors_never_leak_internals_across_many_bad_inputs` |

## Where the contract is ambiguous or silent

Each of these is handled in the tests by accepting a range of outcomes (or by a stated assumption). The contract owner should settle them.

1. **Lying or missing Content-Length.** "Checked before parsing" does not say whether the real byte count or the header is authoritative, or what a mismatched header gets (413 or 400).
2. **Order of checks.** For `/v1/saved`, the contract does not say which comes first: auth (401), size (413), content type (415) or validation (422). It also does not order `UNKNOWN_FIELD` against `INVALID_INPUT` when both apply, or `INVALID_JSON` against 415.
3. **Duplicate JSON keys.** Not addressed. Last-wins parsing could let a value pass one check and be used differently elsewhere.
4. **`NaN` / `Infinity` tokens.** Not addressed. Python's parser accepts them, so the contract should state 400 `INVALID_JSON`.
5. **Content-Type parameters and case.** It does not say whether `application/json; charset=utf-8` or `Application/JSON` is accepted.
6. **UTF-8 BOM and invalid UTF-8** in the body: 400 `INVALID_JSON` or something else?
7. **Explicit `null` for optional fields** (`status`, `category`, `description`, mapping values are allowed to be null, `sign_convention` is). Is `"status": null` accepted as the default?
8. **Required-ness of `start` / `end`.** They appear in the run-options example but are not marked required or optional, and no default window is defined.
9. **Transactions dated outside `start`–`end`**, or outside the scenario range: ignored, or 422 `WINDOW_OUTSIDE_DATA`?
10. **`start == end`, and dates that fall on non-trading days.** Not specified.
11. **Is `description` part of `input_checksum`?** The checksum covers "transactions". If descriptions are hashed, an identical run gets different checksums and a hash of the description persists in saved meta. The tests assume it is excluded (`test_input_checksum_ignores_description`).
12. **Character counting** for `description` (140), `name` (80), column names (100) and `csv` (2,000,000): code points, UTF-16 units or bytes? This matters for emoji and for a JavaScript frontend that counts differently.
13. **Which code a too-long `csv` gets.** "csv text ≤ 2,000,000 characters" could be `INVALID_INPUT` (a size limit) or `CSV_INVALID`. Too many rows is explicitly `CSV_INVALID`, but too many transactions is `INVALID_INPUT`.
14. **CSV header names over 100 characters** in unmapped columns: rejected, truncated or ignored? And which code?
15. **Is `columns` all header columns or only the mapped ones?** SECURITY-PRIVACY says unknown columns are dropped, but `columns` echoes names. The example shows only mapped columns.
16. **Must `mapping` include all 10 keys,** or may omitted keys default to null? What if both `date` and `posted_date` are mapped (precedence for `date_column_used`)?
17. **How sign-convention inference works.** The example infers `debits_positive` from one positive amount. It does not say when inference fails (mixed signs? all negative?). The tests assume mixed signs in a single amount column are not inferable. It also does not say what happens when an explicit `sign_convention` contradicts the mapping (e.g. `separate_columns` with only `amount` mapped), or which `type` column values are recognised.
18. **Row numbers with quoted multi-line fields.** "Line number in the file" (physical line) vs record index.
19. **Problem rows.** Are they included in `transactions` with `amount`/`posted_date` null? What exactly is the `problem` value (`invalid_amount`, …)? Are signed CSV amounts like `+1` valid?
20. **Ragged rows, stray quotes, empty CSV and header-only CSV.** Not specified (200 with 0 rows, or `CSV_INVALID`?). A UTF-8 BOM before the header is also not covered.
21. **Neutralisation scope.** Only column names are listed as echoed. Error messages that mention a missing mapped column could echo a formula; the contract does not say whether messages are neutralised or must avoid echoing.
22. **Parse output vs simulate input.** Parse transactions carry `row` and `problem`, which simulate rejects as `UNKNOWN_FIELD`. The client must strip them; the contract does not say so.
23. **Is `fields` present for `WINDOW_OUTSIDE_DATA`, `SIGN_CONVENTION_REQUIRED`, `CSV_INVALID` and `UNKNOWN_SCENARIO`?** "Validation errors" is not defined precisely. The tests require `fields` only for `UNKNOWN_FIELD` / `INVALID_INPUT` and forbid it only for clearly non-validation codes.
24. **Format of the `fields` path for an unknown key.** Is it `transactions.0.foo` or the parent `transactions.0`? Is a missing required field reported as its own path?
25. **Ill-formed `scenario_id`** (empty, huge, NUL, wrong type): 404 `UNKNOWN_SCENARIO` or 422 `INVALID_INPUT`?
26. **Compare `meta.input_checksum`.** There are two runs (a and b) but only one `meta`. Which input does the checksum cover?
27. **Compare `difference` money format.** "Shown to the cent" does not say whether amounts are strings and whether they carry a sign; the tests assume strings like `-12.34`.
28. **Engine result format.** `engine/fixtures/FORMAT.md` is referenced but not supplied, so the tests check only the named keys (`status`, `summary`, `buys`, `series`, `engine_version`).
29. **Authorization header parsing.** It does not say whether an empty `Bearer `, a non-Bearer scheme or a lowercase `bearer` is `AUTH_REQUIRED` or `AUTH_INVALID`.
30. **Token claim edge cases.** The contract is silent on: `aud` as an array, `nbf` in the future, `iat` in the future, clock-skew leeway, a missing `kid` header, `is_anonymous` as the string `"true"`, and `exp` as a string. It also does not say how a token for a deleted user is refused. SECURITY-PRIVACY §3 says "the API refuses tokens for users that no longer exist", but this is not in the API contract.
31. **Bad `Authorization` header on open endpoints** (`/simulate` with garbage Bearer): ignored or 401?
32. **`SUPABASE_URL` unset, request without token:** 401 or 503 first?
33. **Data API answers other than "did not respond".** A 500, a 401 (expired or deleted user), a 403 (RLS), a non-JSON body or an empty array could map to 503, 500 or 401. The contract only covers "did not respond".
34. **Partial writes.** If the `scenarios` insert succeeds and `scenario_results` fails, there is no rollback or compensating delete, so an orphan scenario remains. The response code is also unspecified.
35. **Storage payload.** Row shapes for `scenarios` / `scenario_results` are not specified: whether `user_id` is sent (RLS `with check` needs it to equal `sub`), the `Content-Profile: app` schema header for the `app` schema, and the exact `transactions` format (cents?). PLAN says "amount cents", while the API takes decimal strings.
36. **Rate limiting.** It does not say whether simulate and compare share one 30/min bucket or have separate buckets, or whether the window is fixed or sliding. Other open points: whether requests rejected with 4xx count, whether `/v1/health` counts toward `read` (uptime pings), and the expected `Retry-After` range. "Per client IP" behind Vercel needs a trusted `X-Forwarded-For` policy; spoofed XFF could bypass or poison the limiter. SECURITY-PRIVACY also mentions per-user limits, which the API contract omits. Whether limiter state is per `create_app` instance is not stated.
37. **`/docs`, `/openapi.json`, `OPTIONS` / CORS preflight, `HEAD`, and unknown query parameters** on GET endpoints: not covered.
38. **Health in degraded state.** The 503 body is `{"status": "degraded", ...}`, not the standard error envelope. That is an exception to "errors always look like this" that should be made explicit.
39. **Exact `meta.label` text.** The contract shows a literal string. The tests assume it is normative.
40. **Exactly-at-limit body.** "At most 3,000,000 bytes" implies 3,000,000 is accepted; the tests assume so.
41. **Generated transactions with `transactions` absent but `generate` present for `/v1/saved` and `save_transactions: true`.** Are generated transactions saved?
42. **Assumptions "sample-data label".** Is it its own list item (and with what `id`), or the R-12.5 entry?
