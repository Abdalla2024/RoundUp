"""Per-client sliding-window rate limits, kept in memory per server instance (see OPERATIONS.md)."""

import math
import threading
import time
from collections import defaultdict, deque

DEFAULT_LIMITS = {"simulate": 30, "compare": 30, "parse": 10, "saved": 10, "read": 120}   # per minute
WINDOW = 60.0
MAX_TRACKED = 50_000


class RateLimiter:
    def __init__(self, limits: dict | None = None, clock=time.monotonic):
        self.limits = {**DEFAULT_LIMITS, **(limits or {})}
        self.clock = clock
        self._hits: dict = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, bucket: str, client: str) -> int:
        """Record a hit. Returns 0 if allowed, otherwise the seconds to wait."""
        now = self.clock()
        key = (bucket, client)
        with self._lock:
            if len(self._hits) > MAX_TRACKED:      # bound memory under a flood of distinct clients
                self._hits.clear()
            q = self._hits[key]
            while q and q[0] <= now - WINDOW:
                q.popleft()
            if len(q) >= self.limits[bucket]:
                return max(1, math.ceil(q[0] + WINDOW - now))
            q.append(now)
            return 0
