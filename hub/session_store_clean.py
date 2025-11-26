"""Clean session store adapter that reuses the shared base implementation."""

from .session_store_base import InMemorySessionStore


class RedisSessionStore:
    """Placeholder RedisSessionStore used in cleanup branch (no runtime Redis)."""
    # Redis-backed session store intentionally removed for runtime simplicity.
    pass


def create_default_store():
    """Factory: always return the in-memory store in the cleanup branch."""
    return InMemorySessionStore()
