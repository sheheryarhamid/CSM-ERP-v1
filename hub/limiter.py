"""Limiter stub: kept for API compatibility after removing Redis-backed
implementation. This stub allows requests and exposes the same methods so
other modules can remain unchanged while the feature is removed.
"""

from typing import Optional


class RateLimiter:
    def __init__(self, window_seconds: int = 60, redis_url: Optional[str] = None):
        self.window = window_seconds

    def allow_request(self, client_id: str, limit: int) -> bool:
        # Allow all requests (no rate limiting in cleanup)
        return True

    def clear(self, client_id: Optional[str] = None) -> None:
        # No state to clear in the stub
        return
