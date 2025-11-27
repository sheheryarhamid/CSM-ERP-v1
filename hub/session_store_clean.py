"""Clean session store adapter that reuses the shared base implementation."""

from .session_store_base import InMemorySessionStore


class RedisSessionStore:  # pylint: disable=too-few-public-methods
    """Placeholder RedisSessionStore used in cleanup branch (no runtime Redis).

    Redis-backed session store intentionally removed for runtime simplicity.
    This placeholder keeps the import surface stable for other modules
    but intentionally provides no runtime methods in the cleanup branch.
    """


def create_default_store():
    """Factory: always return the in-memory store in the cleanup branch."""
    return InMemorySessionStore()
