"""Read and parse a JSON request body safely: size cap before parsing, no floats/NaN/duplicate keys."""

import json

from fastapi import Request
from pydantic import BaseModel, ValidationError

from .errors import ApiError

MAX_BODY = 3_000_000


def _no_constants(name):
    raise ValueError(f"{name} is not allowed")


def _no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key")
    return dict(pairs)


async def read_json(request: Request) -> dict:
    ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if ctype != "application/json":
        raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "Send the request as JSON (Content-Type: application/json).")
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_BODY:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "The request is too large. The limit is 3 MB.")
    chunks, size = [], 0
    async for chunk in request.stream():          # count real bytes; a declared length is not trusted
        size += len(chunk)
        if size > MAX_BODY:
            raise ApiError(413, "PAYLOAD_TOO_LARGE", "The request is too large. The limit is 3 MB.")
        chunks.append(chunk)
    raw = b"".join(chunks)
    try:
        data = json.loads(raw, parse_constant=_no_constants, object_pairs_hook=_no_duplicates)
    except (ValueError, RecursionError, UnicodeDecodeError):
        raise ApiError(400, "INVALID_JSON", "The request body is not valid JSON.") from None
    if not isinstance(data, dict):
        raise ApiError(400, "INVALID_JSON", "The request body must be a JSON object.")
    return data


def validate(model: type[BaseModel], data: dict) -> BaseModel:
    try:
        return model.model_validate(data)
    except ValidationError as e:
        errs = e.errors(include_url=False, include_context=False, include_input=False)
        fields = [".".join(str(p) for p in er["loc"]) for er in errs][:20]
        if any(er["type"] == "extra_forbidden" for er in errs):
            raise ApiError(422, "UNKNOWN_FIELD", "The request contains a field that is not allowed.",
                           fields=[f for f, er in zip(fields, errs) if er["type"] == "extra_forbidden"]) from None
        raise ApiError(422, "INVALID_INPUT", "Some fields are missing or not in the expected format. "
                       "Amounts must be text like \"4.37\" and dates like \"2024-01-31\".", fields=fields) from None
