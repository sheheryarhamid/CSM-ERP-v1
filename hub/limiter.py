"""Rate limiter placeholder - removed in cleanup.

This module previously provided an in-memory RateLimiter. The
functionality was intentionally removed as part of the cleanup.
Keeping this placeholder avoids import errors for lingering
references while signalling removal.
"""

from typing import Any


class RateLimiter:
    """Compatibility shim: raising constructor to fail loudly when used.

    This preserves the public symbol `RateLimiter` for imports while making
    the removal explicit at runtime.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        raise RuntimeError("RateLimiter removed; import or use is not supported in this branch.")
