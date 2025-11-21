"""Simple in-memory rate limiter (sliding-window).

This implementation intentionally does NOT use Redis and is suitable
for single-process development servers. It preserves the original
testable behavior without external dependencies.
"""

from typing import Optional
import threading
import time


class RateLimiter:
    def __init__(self, window_seconds: int = 60, redis_url: Optional[str] = None):
        self.window = window_seconds
        self._lock = threading.Lock()
        self._store: dict[str, list[float]] = {}

    def allow_request(self, client_id: str, limit: int) -> bool:
        now = time.time()
        with self._lock:
            bucket = self._store.setdefault(client_id, [])
            cutoff = now - self.window
            # remove old timestamps
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def clear(self, client_id: Optional[str] = None) -> None:
        with self._lock:
            if client_id:
                self._store.pop(client_id, None)
            else:
                self._store.clear()
