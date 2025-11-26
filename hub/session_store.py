"""Session store glue: expose session-store implementations.

This module keeps the runtime API stable while reusing the shared
`InMemorySessionStore` implementation from `session_store_base`.
"""

import json
import logging
import os
from typing import Any, Optional

from .session_store_base import InMemorySessionStore, _spec_to_kwargs

logger = logging.getLogger(__name__)


class RedisSessionStore:
    """A simple Redis-backed session store using JSON blobs. Not highly optimized — suitable for MVP."""

    def __init__(self, redis_url: str):
        try:
            import redis
        except ImportError as e:
            logger.exception("Redis client library not installed: %s", e)
            raise

        try:
            self.client = redis.from_url(redis_url, decode_responses=True)
            # test connection
            self.client.ping()
        except getattr(redis, "RedisError", Exception) as e:
            logger.exception("Failed to connect to Redis at %s: %s", redis_url, e)
            raise

        self.prefix = "hub:session:"
        self.set_key = "hub:sessions"

    def _key(self, session_id: str) -> str:
        return f"{self.prefix}{session_id}"

    def _now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    def create_session(self, spec: Any):
        """Create a session from a single spec (dict, dataclass, or model)."""
        import uuid

        kw = _spec_to_kwargs(spec)
        session_id = str(uuid.uuid4())
        now = self._now()
        s = {
            "session_id": session_id,
            "user": kw.get("user"),
            "role": kw.get("role"),
            "device": kw.get("device"),
            "store": kw.get("store"),
            "module": kw.get("module"),
            "connection_type": kw.get("connection_type"),
            "start_time": now,
            "last_activity": now,
        }
        key = self._key(session_id)
        self.client.set(key, json.dumps(s))
        self.client.sadd(self.set_key, session_id)
        return s

    def list_sessions(self, *, since_seconds: Optional[int] = None):
        """Return list of sessions stored in Redis (best-effort)."""
        ids = self.client.smembers(self.set_key) or []
        out = []
        for sid in ids:
            try:
                raw = self.client.get(self._key(sid))
                if not raw:
                    # cleanup
                    self.client.srem(self.set_key, sid)
                    continue
                out.append(json.loads(raw))
            except (json.JSONDecodeError, ValueError) as e:
                logger.exception("Failed reading/parsing session %s: %s", sid, e)
        return out

    def get_session(self, session_id: str):
        """Retrieve a single session by id from Redis, or None if missing."""
        raw = self.client.get(self._key(session_id))
        if not raw:
            return None
        return json.loads(raw)

    def terminate_session(self, session_id: str) -> bool:
        """Remove a session and return True when it existed and was deleted."""
        key = self._key(session_id)
        existed = self.client.delete(key)
        self.client.srem(self.set_key, session_id)
        return existed == 1


# Factory to pick backend (Redis or in-memory)
def create_default_store():
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            return RedisSessionStore(redis_url)
        except (ImportError, OSError, RuntimeError) as e:
            logger.warning("Falling back to in-memory session store: %s", e)
    return InMemorySessionStore()
