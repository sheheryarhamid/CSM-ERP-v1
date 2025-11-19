from __future__ import annotations
import os
import threading
import time
from typing import Optional

try:
    import redis
except Exception:
    redis = None


class RateLimiter:
    """Rate limiter with Redis backend when `REDIS_URL` is set, otherwise an in-memory fallback.

    Uses a sliding-window approach in-memory and a Redis sorted-set per client for accuracy across processes.
    """

    def __init__(self, window_seconds: int = 60, redis_url: Optional[str] = None):
        self.window = window_seconds
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self._lock = threading.Lock()
        self._store: dict[str, list[float]] = {}
        # Initialize redis client lazily
        self._redis = None
        if self.redis_url and redis:
            try:
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
            except Exception:
                self._redis = None

    def allow_request(self, client_id: str, limit: int) -> bool:
        """Return True if the request is allowed (and record it), False if rate-limited."""
        now = time.time()
        if self._redis:
            # Use sorted set with timestamps to implement sliding window
            key = f"rate:{client_id}"
            try:
                # Remove old
                self._redis.zremrangebyscore(key, 0, now - self.window)
                # Add current
                self._redis.zadd(key, {str(now): now})
                # Count
                cnt = self._redis.zcard(key)
                # Set TTL slightly longer than window
                self._redis.expire(key, self.window + 5)
                return cnt <= limit
            except Exception:
                # Fallback to in-memory on redis errors
                pass

        # In-memory fallback
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
        """Clear limiter state for a specific client or entirely (for tests)."""
        if self._redis and self.redis_url:
            try:
                if client_id:
                    self._redis.delete(f"rate:{client_id}")
                else:
                    # No reliable cross-process way to clear all keys safely; skip
                    pass
            except Exception:
                pass

        with self._lock:
            if client_id:
                self._store.pop(client_id, None)
            else:
                self._store.clear()
