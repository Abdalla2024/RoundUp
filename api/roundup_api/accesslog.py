"""One JSON log line per request. No bodies, no IPs (salted hash only), no descriptions or amounts."""

import hashlib
import json
import logging
import os
import secrets

log = logging.getLogger("roundup_api.access")
_SALT = os.environ.get("LOG_SALT") or secrets.token_hex(16)


def client_hash(ip: str) -> str:
    return hashlib.sha256(f"{_SALT}:{ip}".encode()).hexdigest()[:12]


def write(**fields) -> None:
    log.info(json.dumps(fields, sort_keys=True))
