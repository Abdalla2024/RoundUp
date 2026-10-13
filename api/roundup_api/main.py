"""FastAPI app (API.md). `create_app()` builds an app; `app` is the default built from the environment."""

import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from roundup_engine import ENGINE_VERSION
from roundup_scenarios import FAMILIES, MODEL_VERSION

from . import accesslog, content, service
from .auth import TokenVerifier
from .body import read_json, validate
from .csv_import import parse_csv
from .errors import ApiError
from .ratelimit import RateLimiter
from .schemas import CompareIn, ParseIn, SaveIn, SimulateIn
from .storage import Storage

ROUTE_BUCKETS = {"/v1/simulate": "simulate", "/v1/compare": "compare", "/v1/transactions/parse": "parse",
                 "/v1/saved": "saved"}
HTTP_CODES = {404: ("NOT_FOUND", "There is nothing at this address."),
              405: ("METHOD_NOT_ALLOWED", "This address does not accept that kind of request.")}


def _client_ip(request: Request) -> str:
    # Vercel overwrites X-Forwarded-For with the real client IP ("to prevent IP spoofing", Vercel request-headers
    # docs). Forwarded headers are trusted only when ROUNDUP_TRUST_PROXY=1 is set explicitly for the deployment;
    # otherwise (e.g. locally) the socket address is used and a client cannot pick its own rate-limit bucket.
    fwd = request.headers.get("x-vercel-forwarded-for") or request.headers.get("x-forwarded-for")
    if fwd and os.environ.get("ROUNDUP_TRUST_PROXY") == "1":
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_app(supabase_url: str | None = None, publishable_key: str | None = None, jwks: dict | None = None,
               storage_transport=None, rate_limits: dict | None = None, slow_ms: int = 2000,
               allowed_origin: str | None = None) -> FastAPI:
    app = FastAPI(title="RoundUp API", version=ENGINE_VERSION, docs_url=None, redoc_url=None, openapi_url=None)
    verifier = TokenVerifier(supabase_url, jwks)
    storage = Storage(supabase_url, publishable_key, storage_transport)
    limiter = RateLimiter(rate_limits)

    @app.middleware("http")
    async def frame(request: Request, call_next):
        request_id = uuid.uuid4().hex                       # never taken from the client
        request.state.request_id = request_id
        started = time.perf_counter()
        ip = _client_ip(request)
        bucket = ROUTE_BUCKETS.get(request.url.path, "read") if request.method == "POST" else "read"
        wait = limiter.check(bucket, ip)
        if wait:
            response = _error(ApiError(429, "RATE_LIMITED", "Too many requests. Please wait a moment and try again.",
                                       headers={"Retry-After": str(wait)}))
        else:
            try:
                response = await call_next(request)
            except Exception:                               # last-resort guard; details never leave the server
                response = _error(ApiError(500, "INTERNAL", "Something went wrong on our side. Please try again."))
        latency = int((time.perf_counter() - started) * 1000)
        response.headers["X-Content-Type-Options"] = "nosniff"        # JSON API: never rendered, never framed
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.method != "GET" or response.status_code >= 400:
            response.headers["Cache-Control"] = "no-store"          # results and errors are never cached
        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={latency}"
        accesslog.write(request_id=request_id, method=request.method, route=request.url.path[:64],
                        status=response.status_code, latency_ms=latency, slow=latency >= slow_ms,
                        client=accesslog.client_hash(ip), engine_version=ENGINE_VERSION,
                        error_code=getattr(request.state, "error_code", None) or response.headers.get("x-error-code"))
        if "x-error-code" in response.headers:
            del response.headers["x-error-code"]
        return response

    def _error(e: ApiError) -> JSONResponse:
        return JSONResponse(e.body(), status_code=e.status, headers={**e.headers, "x-error-code": e.code})

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, e: ApiError):
        return _error(e)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, e: StarletteHTTPException):
        code, msg = HTTP_CODES.get(e.status_code, ("INTERNAL", "Something went wrong on our side. Please try again."))
        return _error(ApiError(e.status_code if e.status_code in HTTP_CODES else 500, code, msg))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, e: RequestValidationError):
        return _error(ApiError(422, "INVALID_INPUT", "The request is not in the expected format."))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, e: Exception):
        return _error(ApiError(500, "INTERNAL", "Something went wrong on our side. Please try again."))

    @app.get("/v1/health")
    def health():
        ok = service.engine_self_check()
        body = {"status": "ok" if ok else "degraded", "engine_version": ENGINE_VERSION,
                "model_version": MODEL_VERSION, "scenarios": len(FAMILIES)}
        return JSONResponse(body, status_code=200 if ok else 503)

    @app.get("/v1/scenarios")
    def scenarios():
        return service.scenarios_listing()

    @app.get("/v1/assumptions")
    def assumptions():
        return {"disclaimer": content.DISCLAIMER,
                "assumptions": [{"id": i, "title": t, "text": x} for i, t, x in content.ASSUMPTIONS]}

    @app.post("/v1/simulate")
    async def simulate(request: Request):
        req = validate(SimulateIn, await read_json(request))
        return service.simulate(req)

    @app.post("/v1/compare")
    async def compare(request: Request):
        req = validate(CompareIn, await read_json(request))
        return service.compare(req)

    @app.post("/v1/transactions/parse")
    async def parse(request: Request):
        req = validate(ParseIn, await read_json(request))
        return parse_csv(req.csv, req.mapping.model_dump(), req.sign_convention)

    @app.post("/v1/saved", status_code=201)
    async def saved(request: Request):
        if not storage.base or not verifier.issuer:
            raise ApiError(503, "STORAGE_UNAVAILABLE", "Saving is not available right now.")
        claims = verifier.verify(request.headers.get("authorization"))      # before reading the body
        token = request.headers["authorization"][7:].strip()
        req = validate(SaveIn, await read_json(request))
        out = service.simulate(req)
        txs = None
        if req.save_transactions:
            txs = [{"posted_date": t["posted_date"], "amount": t["amount"], "direction": t["direction"],
                    "status": t["status"], **({"category": t["category"]} if "category" in t else {})}
                   for t in service.engine_input(req, req.strategy, req.reinvest)[0]["transactions"]]
        m = out["meta"]
        params = {"p_name": req.name, "p_transactions": txs,             # owner = auth.uid() inside the function
                  "p_config": {"scenario_id": req.scenario_id, "style": req.style, "start": req.start,
                               "end": req.end, "strategy": req.strategy, "reinvest": req.reinvest,
                               "generate": req.generate.model_dump() if req.generate else None},
                  "p_market_scenario": m["scenario_id"], "p_style": m["style"], "p_strategy": req.strategy,
                  "p_reinvest": req.reinvest, "p_result": out["result"], "p_engine_version": m["engine_version"],
                  "p_model_version": m["model_version"], "p_scenario_seed": m["scenario_seed"],
                  "p_data_kind": "sample", "p_data_end": out["result"]["summary"]["as_of"],
                  "p_market_checksum": m["market_checksum"], "p_input_checksum": m["input_checksum"]}
        new_id = storage.save(token, params)
        return JSONResponse({"id": new_id, **out}, status_code=201)

    if allowed_origin:      # exactly one origin (owner decision: the web project's default Vercel address)
        app.add_middleware(CORSMiddleware, allow_origins=[allowed_origin], allow_methods=["GET", "POST"],
                           allow_headers=["Content-Type", "Authorization"], allow_credentials=False,
                           expose_headers=["X-Request-ID", "Retry-After"], max_age=600)
    return app


app = create_app(supabase_url=os.environ.get("SUPABASE_URL"),
                 publishable_key=os.environ.get("SUPABASE_PUBLISHABLE_KEY"),
                 allowed_origin=os.environ.get("ALLOWED_ORIGIN"))
