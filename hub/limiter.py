"""Rate limiter placeholder - removed in cleanup.

This module previously provided an in-memory RateLimiter. The
functionality was intentionally removed as part of the cleanup.
Keeping this placeholder avoids import errors for lingering
references while signalling removal.
"""

from typing import Any


def _removed(*args: Any, **kwargs: Any):
    raise RuntimeError("RateLimiter removed; import or use is not supported in this branch.")


# Export a minimal symbol so `from .limiter import RateLimiter` fails loudly
RateLimiter = _removed
