from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
import os
import json
import logging

logger = logging.getLogger(__name__)


class InMemorySessionStore:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_session(self, user: str, role: str, device: Optional[str] = None, store: Optional[str] = None, module: Optional[str] = None, connection_type: Optional[str] = None) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        now = self._now()
        s = {
            "session_id": session_id,
            "user": user,
            "role": role,
            "device": device,
            "store": store,
            "module": module,
            "connection_type": connection_type,
            "start_time": now,
            "last_activity": now,
        }
        self.sessions[session_id] = s
        return s

    def list_sessions(self, *, since_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        # since_seconds unused for now; return all
        return list(self.sessions.values())

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)

    def terminate_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False


class RedisSessionStore:
    """A simple Redis-backed session store using JSON blobs. Not highly optimized — suitable for MVP."""
    def __init__(self, redis_url: str):
        try:
            import redis

            self.client = redis.from_url(redis_url, decode_responses=True)
            # test connection
            self.client.ping()
        except Exception as e:
            logger.exception("Failed to connect to Redis at %s: %s", redis_url, e)
            raise

        self.prefix = "hub:session:"
        self.set_key = "hub:sessions"

    def _key(self, session_id: str) -> str:
        return f"{self.prefix}{session_id}"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_session(self, user: str, role: str, device: Optional[str] = None, store: Optional[str] = None, module: Optional[str] = None, connection_type: Optional[str] = None) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        now = self._now()
        s = {
            "session_id": session_id,
            "user": user,
            "role": role,
            "device": device,
            "store": store,
            "module": module,
            "connection_type": connection_type,
            "start_time": now,
            "last_activity": now,
        }
        key = self._key(session_id)
        self.client.set(key, json.dumps(s))
        self.client.sadd(self.set_key, session_id)
        return s

    def list_sessions(self, *, since_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
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
            except Exception:
                logger.exception("Failed reading session %s", sid)
        return out

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        raw = self.client.get(self._key(session_id))
        if not raw:
            return None
        return json.loads(raw)

    def terminate_session(self, session_id: str) -> bool:
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
        except Exception:
            logger.warning("Falling back to in-memory session store")
    return InMemorySessionStore()
